#!/usr/bin/env python3
"""Dump live closed/open trades + recent events (run on VPS)."""
import json
import sqlite3
from datetime import datetime, timezone

DB = "/opt/tsm-chandelier/data/live/tsm_chandelier_live.sqlite"


def dt(ms):
    if ms is None:
        return None
    return datetime.fromtimestamp(int(ms) / 1000, timezone.utc).isoformat()


con = sqlite3.connect(f"file:{DB}?mode=ro", uri=True)
con.row_factory = sqlite3.Row
print("NOW_UTC", datetime.now(timezone.utc).isoformat())
tables = [r[0] for r in con.execute("select name from sqlite_master where type='table'")]
print("TABLES", tables)
for t in tables:
    n = con.execute(f"select count(*) from {t}").fetchone()[0]
    print(f"COUNT {t}={n}")

print("\n=== OPEN ===")
for r in con.execute("select * from open_trades"):
    d = dict(r)
    d["entry_utc"] = dt(d.get("entry_ts_ms"))
    print(json.dumps(d, default=str)[:2000])

print("\n=== CLOSED ===")
for r in con.execute("select * from closed_trades order by updated_ms"):
    d = dict(r)
    d["created_utc"] = dt(d.get("created_ms"))
    d["updated_utc"] = dt(d.get("updated_ms"))
    d["planned_entry_utc"] = dt(d.get("planned_entry_ts_ms"))
    print(json.dumps(d, default=str)[:3000])

print("\n=== HANDLED ===")
for r in con.execute("select * from handled_entries order by entry_ts_ms"):
    print(json.dumps(dict(r), default=str)[:1500])

print("\n=== EVENTS (entry/exit/stop) ===")
for r in con.execute(
    "select id, ts_utc, symbol, kind, substr(detail_json,1,1200) as d from events "
    "where kind in ('entry_filled','entry_timing','position_closed','time_exit','dry_run_time_exit') "
    "order by id"
):
    print(json.dumps(dict(r), default=str))
