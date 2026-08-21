#!/usr/bin/env python3
"""Import VPS-fetched Binance 1h/1m CSVs into local research_ohlcv.sqlite."""
from __future__ import annotations

import sqlite3
import time
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DB = ROOT / "artifacts" / "datasets" / "research_ohlcv.sqlite"
SRC = ROOT / "artifacts" / "reports" / "tsm_chandelier" / "vps94_ohlcv_fetch"
ENDPOINT = "https://fapi.binance.com/fapi/v1/klines"
SYMBOLS = ["BTCUSDT", "ETHUSDT", "SOLUSDT"]
TFS = ["1h", "1m"]


def utc(ms: int | None) -> str | None:
    if ms is None:
        return None
    return datetime.fromtimestamp(ms / 1000, timezone.utc).isoformat()


def main() -> None:
    now = int(time.time() * 1000)
    con = sqlite3.connect(str(DB))
    total = 0
    for tf in TFS:
        for sym in SYMBOLS:
            path = SRC / f"{sym}_{tf}_binance.csv"
            if not path.exists():
                print("MISSING", path)
                continue
            df = pd.read_csv(path)
            rows = [
                (
                    "binance",
                    sym,
                    tf,
                    int(r.ts_ms),
                    float(r.open),
                    float(r.high),
                    float(r.low),
                    float(r.close),
                    float(r.volume),
                    "last",
                    1,
                    now,
                    "usdt_perp",
                    ENDPOINT,
                )
                for r in df.itertuples(index=False)
            ]
            con.executemany(
                """
                INSERT OR REPLACE INTO market_ohlcv
                (source, symbol, timeframe, ts_ms, open, high, low, close, volume,
                 price_type, is_complete, downloaded_at, product, source_endpoint)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                """,
                rows,
            )
            mx = con.execute(
                "SELECT MIN(ts_ms), MAX(ts_ms), COUNT(*) FROM market_ohlcv "
                "WHERE source='binance' AND symbol=? AND timeframe=? AND is_complete=1",
                (sym, tf),
            ).fetchone()
            print(sym, tf, "upserted", len(rows), "db", utc(mx[0]), "->", utc(mx[1]), "n", mx[2])
            total += len(rows)
    con.execute(
        "INSERT OR REPLACE INTO meta(key, value) VALUES (?, ?)",
        (
            "refresh_ohlcv_via_vps94_binance",
            f"utc={datetime.now(timezone.utc).isoformat()}; rows={total}",
        ),
    )
    con.commit()
    con.close()
    print("done", total)


if __name__ == "__main__":
    main()
