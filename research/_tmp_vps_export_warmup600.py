#!/usr/bin/env python3
"""Export last N Binance 1h bars from VPS shared candles (warmup + live window)."""
import csv
import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

OUT = Path("/tmp/vps94_parity_export")
OUT.mkdir(parents=True, exist_ok=True)
CANDLE_DB = "/var/lib/botsgeneral/shared_candles.db"
N = 600
SYMBOLS = ["BTCUSDT", "ETHUSDT"]

con = sqlite3.connect(f"file:{CANDLE_DB}?mode=ro", uri=True)
meta = {"exported_utc": datetime.now(timezone.utc).isoformat(), "n_requested": N, "symbols": {}}
for sym in SYMBOLS:
    rows = list(
        con.execute(
            "select ts_ms, open, high, low, close, volume from candles "
            "where exchange='binance' and symbol=? and timeframe='1h' "
            "order by ts_ms desc limit ?",
            (sym, N),
        )
    )
    rows = list(reversed(rows))
    path = OUT / f"{sym}_1h_binance_warmup600.csv"
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["ts_ms", "open", "high", "low", "close", "volume"])
        w.writerows(rows)
    meta["symbols"][sym] = {
        "n": len(rows),
        "first_ms": rows[0][0] if rows else None,
        "last_ms": rows[-1][0] if rows else None,
        "path": str(path),
    }
    print(sym, len(rows), rows[0][0] if rows else None, rows[-1][0] if rows else None)
(OUT / "warmup600_meta.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")
print("WROTE", OUT)
