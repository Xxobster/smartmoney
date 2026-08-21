import sqlite3
import time
from pathlib import Path

p = Path(r"D:/projectsdata/candles/market_ohlcv.sqlite")
print("exists", p.exists(), "size_gb", p.stat().st_size / 1e9)
t = time.time()
c = sqlite3.connect(f"file:{p.as_posix()}?mode=ro", uri=True)
print("open_s", time.time() - t)
t = time.time()
row = c.execute(
    "SELECT MAX(ts_ms), COUNT(*) FROM market_ohlcv "
    "WHERE source='binance' AND symbol='BTCUSDT' AND timeframe='1h'"
).fetchone()
print("query", row, "s", time.time() - t)
c.close()
print("ok")
