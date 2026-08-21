#!/usr/bin/env python3
"""Export VPS shared 1h candles + coverage (run on VPS)."""
import csv
import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

OUT = Path("/tmp/vps94_parity_export")
OUT.mkdir(parents=True, exist_ok=True)
CANDLE_DB = "/var/lib/botsgeneral/shared_candles.db"
N_1H = 800
SYMBOLS = ["BTCUSDT", "ETHUSDT", "SOLUSDT"]

con = sqlite3.connect(f"file:{CANDLE_DB}?mode=ro", uri=True)
meta = {"exported_utc": datetime.now(timezone.utc).isoformat(), "symbols": {}}
print("NOW", datetime.now(timezone.utc).isoformat())
for t in [r[0] for r in con.execute("select name from sqlite_master where type='table'")]:
    cols = [c[1] for c in con.execute(f"pragma table_info({t})")]
    print("table", t, cols)

for sym in SYMBOLS:
    for tf in ("1h", "1m"):
        n, mn, mx = con.execute(
            "select count(*), min(ts_ms), max(ts_ms) from candles "
            "where exchange='binance' and symbol=? and timeframe=?",
            (sym, tf),
        ).fetchone()
        print(f"coverage {sym} {tf} n={n} min={mn} max={mx}")
        meta["symbols"][f"{sym}_{tf}"] = {"n": n, "first_ms": mn, "last_ms": mx}
    rows = list(
        con.execute(
            "select ts_ms, open, high, low, close, volume from candles "
            "where exchange='binance' and symbol=? and timeframe='1h' "
            "order by ts_ms desc limit ?",
            (sym, N_1H),
        )
    )
    rows = list(reversed(rows))
    path = OUT / f"{sym}_1h_binance_warmup800.csv"
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["ts_ms", "open", "high", "low", "close", "volume"])
        w.writerows(rows)
    print(sym, "1h export", len(rows), rows[0][0] if rows else None, rows[-1][0] if rows else None)

(OUT / "meta.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")
print("WROTE", OUT)
