#!/usr/bin/env python3
"""Append newest Binance USDT-M 1h and 1m bars into research_ohlcv.sqlite."""
from __future__ import annotations

import json
import sqlite3
import time
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DB = ROOT / "artifacts" / "datasets" / "research_ohlcv.sqlite"
SYMBOLS = ["BTCUSDT", "ETHUSDT", "SOLUSDT"]
ENDPOINT = "https://fapi.binance.com/fapi/v1/klines"
TF_MS = {"1h": 3_600_000, "1m": 60_000}
# 1m: cover live window with a few days of warmup (precise SL/TP path).
ONE_M_FLOOR_MS = int(datetime(2026, 8, 1, tzinfo=timezone.utc).timestamp() * 1000)


def utc(ms: int | None) -> str | None:
    if ms is None:
        return None
    return datetime.fromtimestamp(ms / 1000, timezone.utc).isoformat()


def fetch(symbol: str, interval: str, start_ms: int, end_ms: int) -> list[tuple]:
    step = TF_MS[interval]
    rows: list[tuple] = []
    cursor = start_ms
    now = int(time.time() * 1000)
    while cursor < end_ms:
        url = (
            f"{ENDPOINT}?symbol={symbol}&interval={interval}"
            f"&startTime={cursor}&endTime={end_ms}&limit=1500"
        )
        with urllib.request.urlopen(url, timeout=60) as resp:
            batch = json.loads(resp.read().decode())
        if not batch:
            break
        for k in batch:
            ts = int(k[0])
            close_time = int(k[6])
            if close_time > now:
                continue
            rows.append(
                (
                    "binance",
                    symbol,
                    interval,
                    ts,
                    float(k[1]),
                    float(k[2]),
                    float(k[3]),
                    float(k[4]),
                    float(k[5]),
                    "last",
                    1,
                    now,
                    "usdt_perp",
                    ENDPOINT,
                )
            )
        nxt = int(batch[-1][0]) + step
        if nxt <= cursor:
            break
        cursor = nxt
        time.sleep(0.05)
    return rows


def upsert(con: sqlite3.Connection, rows: list[tuple]) -> None:
    con.executemany(
        """
        INSERT OR REPLACE INTO market_ohlcv
        (source, symbol, timeframe, ts_ms, open, high, low, close, volume,
         price_type, is_complete, downloaded_at, product, source_endpoint)
        VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)
        """,
        rows,
    )
    con.commit()


def max_ts(con: sqlite3.Connection, symbol: str, tf: str) -> int | None:
    row = con.execute(
        """
        SELECT MAX(ts_ms) FROM market_ohlcv
        WHERE source='binance' AND symbol=? AND timeframe=? AND is_complete=1
        """,
        (symbol, tf),
    ).fetchone()
    return int(row[0]) if row and row[0] is not None else None


def main() -> None:
    con = sqlite3.connect(str(DB))
    now = int(time.time() * 1000)
    total = 0
    for tf, step in TF_MS.items():
        end_ms = (now // step) * step
        for sym in SYMBOLS:
            mx = max_ts(con, sym, tf)
            if tf == "1m":
                start = max(ONE_M_FLOOR_MS, (mx + step) if mx else ONE_M_FLOOR_MS)
            else:
                start = (mx + step) if mx else end_ms - 200 * step
            if start >= end_ms:
                print(sym, tf, "already fresh max", utc(mx))
                continue
            print(sym, tf, "fetch", utc(start), "->", utc(end_ms))
            rows = fetch(sym, tf, start, end_ms)
            upsert(con, rows)
            total += len(rows)
            print(sym, tf, "wrote", len(rows), "new_max", utc(max_ts(con, sym, tf)))
    con.execute(
        "INSERT OR REPLACE INTO meta(key, value) VALUES ('refresh_ohlcv_binance_futures', ?)",
        (f"utc={datetime.now(timezone.utc).isoformat()}; rows={total}",),
    )
    con.commit()
    con.close()
    print("done total_rows", total)


if __name__ == "__main__":
    main()
