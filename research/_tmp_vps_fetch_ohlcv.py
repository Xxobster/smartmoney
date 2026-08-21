#!/usr/bin/env python3
"""Fetch Binance USDT-M 1h + 1m klines on VPS and write CSVs (run on VPS)."""
from __future__ import annotations

import csv
import json
import time
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

OUT = Path("/tmp/vps94_ohlcv_fetch")
OUT.mkdir(parents=True, exist_ok=True)
SYMBOLS = ["BTCUSDT", "ETHUSDT", "SOLUSDT"]
ENDPOINT = "https://fapi.binance.com/fapi/v1/klines"
TF_MS = {"1h": 3_600_000, "1m": 60_000}
# 1m from 2026-08-01 (covers live window + warmup)
ONE_M_START = int(datetime(2026, 8, 1, tzinfo=timezone.utc).timestamp() * 1000)
# 1h: last 800 bars is enough for live signals; also dump coverage later from shared DB
ONE_H_START = int(datetime(2026, 7, 1, tzinfo=timezone.utc).timestamp() * 1000)


def utc(ms: int) -> str:
    return datetime.fromtimestamp(ms / 1000, timezone.utc).isoformat()


def fetch(symbol: str, interval: str, start_ms: int, end_ms: int) -> list[list]:
    step = TF_MS[interval]
    rows: list[list] = []
    cursor = start_ms
    now = int(time.time() * 1000)
    while cursor < end_ms:
        url = (
            f"{ENDPOINT}?symbol={symbol}&interval={interval}"
            f"&startTime={cursor}&endTime={end_ms}&limit=1500"
        )
        with urllib.request.urlopen(url, timeout=60) as resp:
            batch = json.loads(resp.read().decode())
        if not batch:
            break
        for k in batch:
            ts = int(k[0])
            close_time = int(k[6])
            if close_time > now:
                continue
            rows.append([ts, float(k[1]), float(k[2]), float(k[3]), float(k[4]), float(k[5])])
        nxt = int(batch[-1][0]) + step
        if nxt <= cursor:
            break
        cursor = nxt
        time.sleep(0.05)
    return rows


def write_csv(path: Path, rows: list[list]) -> None:
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["ts_ms", "open", "high", "low", "close", "volume"])
        w.writerows(rows)


def main() -> None:
    now = int(time.time() * 1000)
    meta = {"exported_utc": datetime.now(timezone.utc).isoformat(), "symbols": {}}
    for tf, start in (("1h", ONE_H_START), ("1m", ONE_M_START)):
        end_ms = (now // TF_MS[tf]) * TF_MS[tf]
        for sym in SYMBOLS:
            print(sym, tf, "fetch", utc(start), "->", utc(end_ms), flush=True)
            rows = fetch(sym, tf, start, end_ms)
            path = OUT / f"{sym}_{tf}_binance.csv"
            write_csv(path, rows)
            meta["symbols"][f"{sym}_{tf}"] = {
                "n": len(rows),
                "first_ms": rows[0][0] if rows else None,
                "last_ms": rows[-1][0] if rows else None,
                "path": str(path),
            }
            print(sym, tf, "wrote", len(rows), flush=True)
    (OUT / "meta.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")
    print("WROTE", OUT)


if __name__ == "__main__":
    main()
