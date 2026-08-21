import sqlite3
from pathlib import Path

for p in [
    Path(r"D:\projects\smartmoney\artifacts\datasets\research_ohlcv.sqlite"),
    Path(r"D:\projectsdata\candles\market_ohlcv.sqlite"),
]:
    con = sqlite3.connect(str(p))
    print("===", p)
    print("market_ohlcv", con.execute("pragma table_info(market_ohlcv)").fetchall())
    try:
        print("meta", con.execute("pragma table_info(meta)").fetchall())
        print("meta sample", con.execute("select * from meta limit 5").fetchall())
    except Exception as e:
        print("meta err", e)
    # BTC source values
    print(
        "BTC sources",
        con.execute(
            "select source, timeframe, count(*) from market_ohlcv where symbol='BTCUSDT' group by 1,2 order by 2,1"
        ).fetchall()[:20],
    )
    con.close()
