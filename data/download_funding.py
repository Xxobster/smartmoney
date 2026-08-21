"""Download signed Binance USDT-M perpetual funding history into SQLite.

If the download fails, research must label the run as lacking funding evidence
(Gate A honesty) and either use a SPOT_PROXY product class or mark funding as
UNKNOWN / zero with an explicit flag — never silently invent rates.
"""
from __future__ import annotations

import argparse
import sqlite3
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, List, Optional

import requests

from paths import DATASETS, DOWNLOAD_CKPT, ensure_artifact_dirs

BINANCE_FUNDING_URL = "https://fapi.binance.com/fapi/v1/fundingRate"
DEFAULT_SYMBOLS = ["BTCUSDT", "ETHUSDT"]


def _ensure_schema(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS funding (
          venue TEXT NOT NULL,
          symbol TEXT NOT NULL,
          funding_time_ms INTEGER NOT NULL,
          funding_rate REAL NOT NULL,
          mark_price REAL,
          downloaded_at_ms INTEGER NOT NULL,
          PRIMARY KEY (venue, symbol, funding_time_ms)
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS funding_meta (
          key TEXT PRIMARY KEY,
          value TEXT NOT NULL
        )
        """
    )
    conn.commit()


def _fetch_page(
    symbol: str,
    start_ms: Optional[int],
    end_ms: Optional[int],
    limit: int = 1000,
) -> List[dict]:
    params = {"symbol": symbol, "limit": limit}
    if start_ms is not None:
        params["startTime"] = start_ms
    if end_ms is not None:
        params["endTime"] = end_ms
    r = requests.get(BINANCE_FUNDING_URL, params=params, timeout=30)
    r.raise_for_status()
    return r.json()


def download_symbol(
    conn: sqlite3.Connection,
    symbol: str,
    start_ms: Optional[int] = None,
    sleep_s: float = 0.2,
) -> int:
    """Paginate funding history backward for one symbol. Returns rows written."""
    inserted = 0
    end_ms: Optional[int] = None
    now_ms = int(time.time() * 1000)
    earliest_wanted = start_ms if start_ms is not None else 0
    while True:
        page = _fetch_page(symbol, start_ms=None, end_ms=end_ms)
        if not page:
            break
        rows = [
            (
                "binance",
                symbol,
                int(item["fundingTime"]),
                float(item["fundingRate"]),
                float(item["markPrice"]) if item.get("markPrice") not in (None, "") else None,
                now_ms,
            )
            for item in page
            if int(item["fundingTime"]) >= earliest_wanted
        ]
        if rows:
            conn.executemany(
                """
                INSERT OR REPLACE INTO funding
                  (venue, symbol, funding_time_ms, funding_rate, mark_price, downloaded_at_ms)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                rows,
            )
            conn.commit()
            inserted += len(rows)
        first_t = int(page[0]["fundingTime"])
        if first_t <= earliest_wanted:
            break
        # Walk backward
        end_ms = first_t - 1
        if len(page) < 1000:
            # Still walk back in case API returns fewer than limit near history start
            if first_t <= earliest_wanted + 1:
                break
        time.sleep(sleep_s)
        # Safety: avoid infinite loop
        if inserted > 200_000:
            break
    return inserted


def download_funding(
    symbols: Iterable[str] = DEFAULT_SYMBOLS,
    db_path: Optional[Path] = None,
    start_ms: Optional[int] = None,
) -> Path:
    ensure_artifact_dirs()
    db_path = db_path or (DATASETS / "funding.sqlite")
    DOWNLOAD_CKPT.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_path))
    try:
        _ensure_schema(conn)
        total = 0
        errors: list[str] = []
        for sym in symbols:
            try:
                n = download_symbol(conn, sym, start_ms=start_ms)
                total += n
                print(f"{sym}: {n} funding rows")
            except Exception as exc:  # noqa: BLE001 — record and continue
                errors.append(f"{sym}: {exc}")
                print(f"ERROR {sym}: {exc}")
        status = "ok" if not errors else "partial_or_failed"
        conn.execute(
            "INSERT OR REPLACE INTO funding_meta(key, value) VALUES (?, ?)",
            ("last_download_utc", datetime.now(timezone.utc).isoformat()),
        )
        conn.execute(
            "INSERT OR REPLACE INTO funding_meta(key, value) VALUES (?, ?)",
            ("status", status),
        )
        conn.execute(
            "INSERT OR REPLACE INTO funding_meta(key, value) VALUES (?, ?)",
            ("errors", "; ".join(errors) if errors else ""),
        )
        conn.execute(
            "INSERT OR REPLACE INTO funding_meta(key, value) VALUES (?, ?)",
            ("rows_written", str(total)),
        )
        conn.commit()
        if status != "ok":
            print(
                "WARNING: funding download incomplete. "
                "Label research as funding_UNKNOWN or use SPOT_PROXY."
            )
    finally:
        conn.close()
    return db_path


def funding_available(db_path: Optional[Path] = None) -> bool:
    db_path = db_path or (DATASETS / "funding.sqlite")
    if not db_path.exists():
        return False
    conn = sqlite3.connect(str(db_path))
    try:
        n = conn.execute("SELECT COUNT(*) FROM funding").fetchone()[0]
        return int(n) > 0
    except sqlite3.Error:
        return False
    finally:
        conn.close()


def main() -> None:
    p = argparse.ArgumentParser(description="Download Binance USDT-M funding history")
    p.add_argument("--symbols", nargs="+", default=DEFAULT_SYMBOLS)
    p.add_argument("--start-ms", type=int, default=None)
    args = p.parse_args()
    path = download_funding(symbols=args.symbols, start_ms=args.start_ms)
    print(f"Funding DB -> {path}")


if __name__ == "__main__":
    main()
