import sqlite3
from pathlib import Path

paths = [
    Path(r"D:\projects\smartmoney\artifacts\datasets\research_ohlcv.sqlite"),
    Path(r"D:\projectsdata\candles\market_ohlcv.sqlite"),
    Path(r"D:\projectsdata\market_ohlcv.sqlite"),
]
for p in paths:
    print("===", p, "exists", p.exists())
    if not p.exists():
        continue
    con = sqlite3.connect(str(p))
    try:
        tables = [r[0] for r in con.execute("select name from sqlite_master where type='table'").fetchall()]
        print("tables", tables[:20])
        for t in tables:
            cols = [c[1] for c in con.execute(f"pragma table_info({t})").fetchall()]
            if "symbol" in cols:
                q = f"select count(*) from {t} where symbol='SOLUSDT'"
                try:
                    n = con.execute(q).fetchone()[0]
                except Exception as e:
                    print(t, "query err", e)
                    continue
                print(t, "SOLUSDT rows", n)
                if n and "timeframe" in cols:
                    rows = con.execute(
                        f"select timeframe, count(*), min(ts_ms), max(ts_ms) from {t} "
                        f"where symbol='SOLUSDT' group by timeframe order by 1"
                    ).fetchall()
                    for r in rows:
                        print(" ", r)
    finally:
        con.close()
