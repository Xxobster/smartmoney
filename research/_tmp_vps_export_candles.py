#!/usr/bin/env python3
"""Export recent VPS Binance 1h/1m candles for live vs backtest re-sim."""
import csv
import json
import sqlite3
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path

OUT = Path("/tmp/vps94_parity_export")
OUT.mkdir(parents=True, exist_ok=True)
CANDLE_DB = "/var/lib/botsgeneral/shared_candles.db"
SINCE = 1786233600000  # 2026-08-09 00:00 UTC
SYMBOLS = ["BTCUSDT", "ETHUSDT", "SOLUSDT"]

print("date_cmd:", subprocess.getoutput("date -u"))
print("collector:", subprocess.getoutput("systemctl is-active botsgeneral-collector@94.156.189.76.service"))
print("time.time", time.time())

con = sqlite3.connect(f"file:{CANDLE_DB}?mode=ro", uri=True)
tables = [r[0] for r in con.execute("select name from sqlite_master where type='table'")]
print("tables", tables)
cols = [c[1] for c in con.execute("pragma table_info(candles)")]
print("candles_cols", cols)

meta = {
    "exported_utc": datetime.now(timezone.utc).isoformat(),
    "since_ms": SINCE,
    "symbols": {},
}

for sym in SYMBOLS:
    for tf in ("1h", "1m"):
        q = (
            "select ts_ms, open, high, low, close, volume from candles "
            "where exchange='binance' and symbol=? and timeframe=? and ts_ms>=? "
            "order by ts_ms"
        )
        rows = list(con.execute(q, (sym, tf, SINCE)))
        path = OUT / f"{sym}_{tf}_binance.csv"
        with path.open("w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(["ts_ms", "open", "high", "low", "close", "volume"])
            w.writerows(rows)
        last = rows[-1][0] if rows else None
        meta["symbols"][f"{sym}_{tf}"] = {
            "n": len(rows),
            "first_ms": rows[0][0] if rows else None,
            "last_ms": last,
            "path": str(path),
        }
        print(sym, tf, "n", len(rows), "last", last)

(OUT / "meta.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")
print("WROTE", OUT)
