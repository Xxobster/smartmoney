"""Persistent live-bot state (handled entries, open trade metadata)."""

from __future__ import annotations

import json
import sqlite3
import time
from pathlib import Path
from typing import Any


class LiveState:
    def __init__(self, db_path: Path | str):
        self.path = Path(db_path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._init()

    def _connect(self) -> sqlite3.Connection:
        # Several symbol processes share one file, so use Write-Ahead Logging (WAL)
        # and a busy timeout instead of failing on concurrent writes.
        con = sqlite3.connect(self.path, timeout=30)
        con.execute("PRAGMA journal_mode=WAL")
        con.execute("PRAGMA busy_timeout=30000")
        con.execute("PRAGMA synchronous=NORMAL")
        return con

    def _init(self) -> None:
        with self._connect() as con:
            con.execute(
                """
                CREATE TABLE IF NOT EXISTS handled_entries (
                    symbol TEXT NOT NULL,
                    entry_ts_ms INTEGER NOT NULL,
                    side TEXT,
                    detail_json TEXT,
                    created_utc TEXT,
                    PRIMARY KEY (symbol, entry_ts_ms)
                )
                """
            )
            con.execute(
                """
                CREATE TABLE IF NOT EXISTS open_trades (
                    symbol TEXT PRIMARY KEY,
                    side TEXT NOT NULL,
                    entry_ts_ms INTEGER NOT NULL,
                    entry_price REAL,
                    stop_price REAL,
                    target_price REAL,
                    qty REAL,
                    leverage INTEGER,
                    position_idx INTEGER,
                    pattern TEXT,
                    detail_json TEXT,
                    created_utc TEXT
                )
                """
            )
            con.execute(
                """
                CREATE TABLE IF NOT EXISTS events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    ts_utc TEXT NOT NULL,
                    symbol TEXT,
                    kind TEXT,
                    detail_json TEXT
                )
                """
            )
            # Realized round trips as reported by the exchange (authoritative for analysis).
            con.execute(
                """
                CREATE TABLE IF NOT EXISTS closed_trades (
                    order_id TEXT PRIMARY KEY,
                    symbol TEXT NOT NULL,
                    side TEXT,
                    qty REAL,
                    avg_entry_price REAL,
                    avg_exit_price REAL,
                    closed_pnl REAL,
                    cum_entry_value REAL,
                    cum_exit_value REAL,
                    leverage REAL,
                    created_ms INTEGER,
                    updated_ms INTEGER,
                    exec_type TEXT,
                    planned_stop REAL,
                    planned_target REAL,
                    planned_entry_ts_ms INTEGER,
                    pattern TEXT,
                    raw_json TEXT,
                    recorded_utc TEXT
                )
                """
            )
            # Chronological wallet mark-to-market, required for daily Sharpe later.
            con.execute(
                """
                CREATE TABLE IF NOT EXISTS equity_snapshots (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    ts_ms INTEGER NOT NULL,
                    ts_utc TEXT NOT NULL,
                    symbol TEXT NOT NULL,
                    wallet_balance REAL,
                    total_equity REAL,
                    available REAL,
                    position_size REAL,
                    position_side TEXT,
                    position_entry REAL,
                    unrealised_pnl REAL,
                    mark_price REAL,
                    liq_price REAL,
                    leverage REAL
                )
                """
            )
            con.execute(
                "CREATE INDEX IF NOT EXISTS idx_equity_ts ON equity_snapshots(ts_ms)"
            )
            # Actual funding paid/received, to compare against backtest funding assumptions.
            con.execute(
                """
                CREATE TABLE IF NOT EXISTS funding_events (
                    tx_id TEXT PRIMARY KEY,
                    symbol TEXT NOT NULL,
                    ts_ms INTEGER,
                    funding REAL,
                    cash_flow REAL,
                    size REAL,
                    side TEXT,
                    raw_json TEXT,
                    recorded_utc TEXT
                )
                """
            )

    def entry_handled(self, symbol: str, entry_ts_ms: int) -> bool:
        with self._connect() as con:
            row = con.execute(
                "SELECT 1 FROM handled_entries WHERE symbol=? AND entry_ts_ms=?",
                (symbol, int(entry_ts_ms)),
            ).fetchone()
        return row is not None

    def handled_detail(self, symbol: str, entry_ts_ms: int) -> dict[str, Any] | None:
        with self._connect() as con:
            row = con.execute(
                "SELECT detail_json FROM handled_entries WHERE symbol=? AND entry_ts_ms=?",
                (symbol, int(entry_ts_ms)),
            ).fetchone()
        if not row or not row[0]:
            return None
        try:
            data = json.loads(row[0])
        except json.JSONDecodeError:
            return None
        return data if isinstance(data, dict) else None

    def mark_entry_handled(self, symbol: str, entry_ts_ms: int, side: str, detail: dict[str, Any]) -> None:
        existing = self.handled_detail(symbol, entry_ts_ms)
        # A later stale/in_position skip must not erase a real fill record.
        if existing is not None and not existing.get("skipped") and detail.get("skipped"):
            return
        with self._connect() as con:
            con.execute(
                """
                INSERT OR REPLACE INTO handled_entries
                (symbol, entry_ts_ms, side, detail_json, created_utc)
                VALUES (?,?,?,?,?)
                """,
                (
                    symbol,
                    int(entry_ts_ms),
                    side,
                    json.dumps(detail, default=str),
                    time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                ),
            )

    def get_open_trade(self, symbol: str) -> dict[str, Any] | None:
        with self._connect() as con:
            row = con.execute(
                """
                SELECT symbol, side, entry_ts_ms, entry_price, stop_price, target_price,
                       qty, leverage, position_idx, pattern, detail_json
                FROM open_trades WHERE symbol=?
                """,
                (symbol,),
            ).fetchone()
        if not row:
            return None
        return {
            "symbol": row[0],
            "side": row[1],
            "entry_ts_ms": int(row[2]),
            "entry_price": float(row[3] or 0),
            "stop_price": float(row[4] or 0),
            "target_price": float(row[5] or 0),
            "qty": float(row[6] or 0),
            "leverage": int(row[7] or 1),
            "position_idx": int(row[8] or 0),
            "pattern": row[9],
            "detail": json.loads(row[10] or "{}"),
        }

    def set_open_trade(self, trade: dict[str, Any]) -> None:
        with self._connect() as con:
            con.execute(
                """
                INSERT OR REPLACE INTO open_trades
                (symbol, side, entry_ts_ms, entry_price, stop_price, target_price,
                 qty, leverage, position_idx, pattern, detail_json, created_utc)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?)
                """,
                (
                    trade["symbol"],
                    trade["side"],
                    int(trade["entry_ts_ms"]),
                    float(trade.get("entry_price") or 0),
                    float(trade.get("stop_price") or 0),
                    float(trade.get("target_price") or 0),
                    float(trade.get("qty") or 0),
                    int(trade.get("leverage") or 1),
                    int(trade.get("position_idx") or 0),
                    trade.get("pattern"),
                    json.dumps(trade.get("detail") or {}, default=str),
                    time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                ),
            )

    def clear_open_trade(self, symbol: str) -> None:
        with self._connect() as con:
            con.execute("DELETE FROM open_trades WHERE symbol=?", (symbol,))

    def log_event(self, symbol: str, kind: str, detail: dict[str, Any] | None = None) -> None:
        with self._connect() as con:
            con.execute(
                "INSERT INTO events (ts_utc, symbol, kind, detail_json) VALUES (?,?,?,?)",
                (
                    time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                    symbol,
                    kind,
                    json.dumps(detail or {}, default=str),
                ),
            )

    def record_closed_trades(
        self,
        symbol: str,
        rows: list[dict[str, Any]],
        *,
        planned: dict[str, Any] | None = None,
    ) -> int:
        """Insert exchange-reported closed round trips. Returns number of new rows."""
        if not rows:
            return 0
        now = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        planned = planned or {}
        new = 0
        with self._connect() as con:
            for r in rows:
                oid = str(r.get("orderId") or f"{symbol}:{r.get('updatedTime')}")
                exists = con.execute(
                    "SELECT 1 FROM closed_trades WHERE order_id=?", (oid,)
                ).fetchone()
                if exists:
                    continue
                con.execute(
                    """
                    INSERT INTO closed_trades
                    (order_id, symbol, side, qty, avg_entry_price, avg_exit_price, closed_pnl,
                     cum_entry_value, cum_exit_value, leverage, created_ms, updated_ms, exec_type,
                     planned_stop, planned_target, planned_entry_ts_ms, pattern, raw_json, recorded_utc)
                    VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                    """,
                    (
                        oid,
                        symbol,
                        r.get("side"),
                        _f(r.get("qty")),
                        _f(r.get("avgEntryPrice")),
                        _f(r.get("avgExitPrice")),
                        _f(r.get("closedPnl")),
                        _f(r.get("cumEntryValue")),
                        _f(r.get("cumExitValue")),
                        _f(r.get("leverage")),
                        _i(r.get("createdTime")),
                        _i(r.get("updatedTime")),
                        r.get("execType"),
                        _f(planned.get("stop_price")),
                        _f(planned.get("target_price")),
                        _i(planned.get("entry_ts_ms")),
                        planned.get("pattern"),
                        json.dumps(r, default=str),
                        now,
                    ),
                )
                new += 1
        return new

    def snapshot_equity(self, symbol: str, ts_ms: int, wallet: dict[str, Any], position: dict[str, Any] | None) -> None:
        pos = position or {}
        with self._connect() as con:
            con.execute(
                """
                INSERT INTO equity_snapshots
                (ts_ms, ts_utc, symbol, wallet_balance, total_equity, available,
                 position_size, position_side, position_entry, unrealised_pnl,
                 mark_price, liq_price, leverage)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)
                """,
                (
                    int(ts_ms),
                    time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(ts_ms / 1000)),
                    symbol,
                    _f(wallet.get("wallet_balance")),
                    _f(wallet.get("total_equity")),
                    _f(wallet.get("available")),
                    _f(pos.get("size")),
                    pos.get("side") or None,
                    _f(pos.get("avgPrice")),
                    _f(pos.get("unrealisedPnl")),
                    _f(pos.get("markPrice")),
                    _f(pos.get("liqPrice")),
                    _f(pos.get("leverage")),
                ),
            )

    def record_funding(self, symbol: str, rows: list[dict[str, Any]]) -> int:
        if not rows:
            return 0
        now = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        new = 0
        with self._connect() as con:
            for r in rows:
                tx_id = str(r.get("id") or f"{symbol}:{r.get('transactionTime')}")
                if con.execute("SELECT 1 FROM funding_events WHERE tx_id=?", (tx_id,)).fetchone():
                    continue
                # Bybit SETTLEMENT rows often leave cashFlow=0 and put the USDT
                # wallet impact in `funding` / `change` (sign = wallet credit).
                funding_amt = _f(r.get("funding"))
                cash_flow = _f(r.get("cashFlow"))
                change = _f(r.get("change"))
                if cash_flow in (None, 0.0) and change not in (None,):
                    cash_flow = change
                elif cash_flow in (None, 0.0) and funding_amt not in (None,):
                    cash_flow = funding_amt
                con.execute(
                    """
                    INSERT INTO funding_events
                    (tx_id, symbol, ts_ms, funding, cash_flow, size, side, raw_json, recorded_utc)
                    VALUES (?,?,?,?,?,?,?,?,?)
                    """,
                    (
                        tx_id,
                        symbol,
                        _i(r.get("transactionTime")),
                        funding_amt,
                        cash_flow,
                        _f(r.get("size")),
                        r.get("side"),
                        json.dumps(r, default=str),
                        now,
                    ),
                )
                new += 1
        return new


def _f(v: Any) -> float | None:
    try:
        if v is None or v == "":
            return None
        return float(v)
    except (TypeError, ValueError):
        return None


def _i(v: Any) -> int | None:
    try:
        if v is None or v == "":
            return None
        return int(float(v))
    except (TypeError, ValueError):
        return None
