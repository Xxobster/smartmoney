"""Append-only research trial registry (SQLite)."""
from __future__ import annotations

import hashlib
import json
import sqlite3
import time
from pathlib import Path
from typing import Any, Optional

from paths import REGISTRY_DB, ensure_artifact_dirs


SCHEMA = """
CREATE TABLE IF NOT EXISTS trials (
  trial_id INTEGER PRIMARY KEY AUTOINCREMENT,
  created_ms INTEGER NOT NULL,
  root_seed INTEGER NOT NULL,
  fold_id INTEGER,
  stage TEXT NOT NULL,
  symbol TEXT,
  proposal_source TEXT,
  params_json TEXT NOT NULL,
  params_hash TEXT NOT NULL,
  metrics_json TEXT,
  status TEXT NOT NULL,
  notes TEXT
);
CREATE TABLE IF NOT EXISTS freezes (
  freeze_id INTEGER PRIMARY KEY AUTOINCREMENT,
  created_ms INTEGER NOT NULL,
  params_hash TEXT NOT NULL,
  params_json TEXT NOT NULL,
  selection_basis TEXT NOT NULL,
  code_version TEXT,
  UNIQUE(params_hash)
);
CREATE TABLE IF NOT EXISTS events (
  event_id INTEGER PRIMARY KEY AUTOINCREMENT,
  created_ms INTEGER NOT NULL,
  kind TEXT NOT NULL,
  payload_json TEXT NOT NULL
);
"""


class TrialRegistry:
    def __init__(self, path: Optional[Path] = None):
        ensure_artifact_dirs()
        self.path = path or REGISTRY_DB
        self.conn = sqlite3.connect(str(self.path))
        self.conn.execute("PRAGMA journal_mode=WAL;")
        self.conn.executescript(SCHEMA)
        self.conn.commit()

    def close(self) -> None:
        self.conn.close()

    @staticmethod
    def hash_params(params: dict) -> str:
        blob = json.dumps(params, sort_keys=True, default=str)
        return hashlib.sha256(blob.encode("utf-8")).hexdigest()

    def log_trial(
        self,
        *,
        root_seed: int,
        stage: str,
        params: dict,
        status: str,
        fold_id: Optional[int] = None,
        symbol: Optional[str] = None,
        proposal_source: Optional[str] = None,
        metrics: Optional[dict] = None,
        notes: str = "",
    ) -> int:
        h = self.hash_params(params)
        cur = self.conn.execute(
            """
            INSERT INTO trials(
              created_ms, root_seed, fold_id, stage, symbol, proposal_source,
              params_json, params_hash, metrics_json, status, notes
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                int(time.time() * 1000),
                int(root_seed),
                fold_id,
                stage,
                symbol,
                proposal_source,
                json.dumps(params, sort_keys=True, default=str),
                h,
                json.dumps(metrics or {}, sort_keys=True, default=str),
                status,
                notes,
            ),
        )
        self.conn.commit()
        return int(cur.lastrowid)

    def count_trials(self) -> int:
        return int(self.conn.execute("SELECT COUNT(*) FROM trials").fetchone()[0])

    def freeze_candidate(
        self,
        params: dict,
        selection_basis: str,
        code_version: str = "0.1.0",
    ) -> str:
        h = self.hash_params(params)
        self.conn.execute(
            """
            INSERT OR REPLACE INTO freezes(created_ms, params_hash, params_json, selection_basis, code_version)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                int(time.time() * 1000),
                h,
                json.dumps(params, sort_keys=True, default=str),
                selection_basis,
                code_version,
            ),
        )
        self.conn.commit()
        return h

    def latest_freeze(self) -> Optional[dict]:
        row = self.conn.execute(
            "SELECT params_hash, params_json, selection_basis, created_ms FROM freezes ORDER BY freeze_id DESC LIMIT 1"
        ).fetchone()
        if not row:
            return None
        return {
            "params_hash": row[0],
            "params": json.loads(row[1]),
            "selection_basis": row[2],
            "created_ms": row[3],
        }

    def log_event(self, kind: str, payload: Any) -> None:
        self.conn.execute(
            "INSERT INTO events(created_ms, kind, payload_json) VALUES (?, ?, ?)",
            (int(time.time() * 1000), kind, json.dumps(payload, default=str)),
        )
        self.conn.commit()
