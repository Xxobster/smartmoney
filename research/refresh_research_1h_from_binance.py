#!/usr/bin/env python3
"""Append newest Binance USDT-M futures 1h bars into local research_ohlcv.sqlite."""
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


def utc(ms: int) -> str:
    return datetime.fromtimestamp(ms / 1000, timezone.utc).isoformat()


def fetch(symbol: str, start_ms: int, end_ms: int) -> list[tuple]:
    rows: list[tuple] = []
    cursor = start_ms
    now = int(time.time() * 1000)
    while cursor < end_ms:
        url = f"{ENDPOINT}?symbol={symbol}&interval=1h&startTime={cursor}&endTime={end_ms}&limit=1500"
        with urllib.request.urlopen(url, timeout=60) as resp:
            batch = json.loads(resp.read().decode())
        if not batch:
            break
        for k in batch:
            ts = int(k[0])
            # only complete bars (close time <= now)
            close_time = int(k[6])
            if close_time > now:
                continue
            rows.append(
                (
                    "binance",
                    symbol,
                    "1h",
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
        nxt = int(batch[-1][0]) + 3_600_000
        if nxt <= cursor:
            break
        cursor = nxt
    return rows


def main() -> None:
    con = sqlite3.connect(str(DB))
    hour = 3_600_000
    now = int(time.time() * 1000)
    end_ms = (now // hour) * hour  # exclusive current open
    total = 0
    for sym in SYMBOLS:
        mx = con.execute(
            """
            SELECT MAX(ts_ms) FROM market_ohlcv
            WHERE source='binance' AND symbol=? AND timeframe='1h' AND is_complete=1
            """,
            (sym,),
        ).fetchone()[0]
        start = int(mx) + hour if mx else end_ms - 200 * hour
        if start >= end_ms:
            print(sym, "already fresh max", utc(mx))
            continue
        print(sym, "fetch", utc(start), "->", utc(end_ms))
        rows = fetch(sym, start, end_ms)
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
        total += len(rows)
        new_mx = con.execute(
            """
            SELECT MAX(ts_ms) FROM market_ohlcv
            WHERE source='binance' AND symbol=? AND timeframe='1h' AND is_complete=1
            """,
            (sym,),
        ).fetchone()[0]
        print(sym, "wrote", len(rows), "new_max", utc(new_mx) if new_mx else None)
    con.execute(
        "INSERT OR REPLACE INTO meta(key, value) VALUES ('refresh_1h_binance_futures', ?)",
        (f"utc={datetime.now(timezone.utc).isoformat()}; rows={total}",),
    )
    con.commit()
    con.close()
    print("done total_rows", total)


if __name__ == "__main__":
    main()
