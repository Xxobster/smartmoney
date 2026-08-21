#!/usr/bin/env python3
"""Print OHLCV coverage for chandelier symbols."""
from datetime import datetime, timezone
from pathlib import Path
import sqlite3

def utc(ms):
    if ms is None:
        return None
    return datetime.fromtimestamp(ms / 1000, timezone.utc).isoformat()

paths = [
    Path(r"d:\projects\smartmoney\artifacts\datasets\research_ohlcv.sqlite"),
    Path(r"D:\projectsdata\candles\market_ohlcv.sqlite"),
]
for p in paths:
    print("====", p, "exists", p.exists())
    if not p.exists():
        continue
    print("size_mb", round(p.stat().st_size / 1e6, 1))
    con = sqlite3.connect(f"file:{p}?mode=ro", uri=True)
    tables = [r[0] for r in con.execute("select name from sqlite_master where type='table'")]
    print("tables", tables[:15])
    for t in tables:
        cols = [c[1] for c in con.execute(f"pragma table_info({t})")]
        if "symbol" in cols and "timeframe" in cols and "ts_ms" in cols:
            print("using", t)
            for sym in ["BTCUSDT", "ETHUSDT", "SOLUSDT"]:
                for tf in ["1h", "1m"]:
                    q = (
                        f"select count(*), min(ts_ms), max(ts_ms) from {t} "
                        "where source='binance' and symbol=? and timeframe=?"
                    )
                    if "is_complete" in cols:
                        q += " and is_complete=1"
                    row = con.execute(q, (sym, tf)).fetchone()
                    print(f"  {sym} {tf}: n={row[0]} min={utc(row[1])} max={utc(row[2])}")
            break
    con.close()
