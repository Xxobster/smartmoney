#!/usr/bin/env python3
import csv
import hashlib
import sqlite3
from pathlib import Path

db = "/var/lib/botsgeneral/shared_candles.db"
out = Path("/tmp/chand_parity")
out.mkdir(exist_ok=True)
con = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
warmup = 500
for sym in ["BTCUSDT", "ETHUSDT", "SOLUSDT"]:
    rows = con.execute(
        "SELECT ts_ms,open,high,low,close,volume FROM candles "
        "WHERE exchange=? AND symbol=? AND timeframe=? ORDER BY ts_ms",
        ("binance", sym, "1h"),
    ).fetchall()
    cols = ["ts_ms", "open", "high", "low", "close", "volume"]
    with (out / f"{sym}_1h_binance.csv").open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow(cols)
        w.writerows(rows)
    tail = rows[-warmup:] if len(rows) > warmup else rows
    with (out / f"{sym}_1h_binance_warmup400.csv").open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow(cols)
        w.writerows(tail)
    print(sym, "n", len(rows), "last", rows[-1][0] if rows else None)

ldb = "/opt/tsm-chandelier/data/live/tsm_chandelier_live.sqlite"
lc = sqlite3.connect(ldb)
lc.row_factory = sqlite3.Row
print("OPEN", [dict(r) for r in lc.execute("SELECT symbol,side,entry_ts_ms,entry_price,stop_price,target_price,qty FROM open_trades")])
print(
    "CLOSED",
    [
        dict(r)
        for r in lc.execute(
            "SELECT symbol,side,qty,avg_entry_price,avg_exit_price,closed_pnl,"
            "planned_stop,planned_target,planned_entry_ts_ms,recorded_utc FROM closed_trades"
        )
    ],
)
print(
    "HANDLED",
    [
        dict(r)
        for r in lc.execute(
            "SELECT symbol,entry_ts_ms,side,substr(detail_json,1,240) d FROM handled_entries ORDER BY entry_ts_ms"
        )
    ],
)
print(
    "EVENTS",
    [
        dict(r)
        for r in lc.execute(
            "SELECT ts_utc,symbol,kind,substr(detail_json,1,200) d FROM events "
            "WHERE kind IN ('entry_filled','entry_timing') ORDER BY id"
        )
    ],
)
for p in [
    "/opt/tsm-chandelier/src/chand/signals_core.py",
    "/opt/tsm-chandelier/src/chand/live/signals.py",
    "/opt/tsm-chandelier/src/chand/live/bot.py",
]:
    h = hashlib.sha256(Path(p).read_bytes()).hexdigest()[:16]
    print("HASH", p, h)
