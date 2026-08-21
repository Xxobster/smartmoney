#!/usr/bin/env python3
"""On VPS: complete Binance 1h signals vs current shared DB (may be gapped)."""

from __future__ import annotations

import json
import sqlite3
import sys
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

sys.path.insert(0, "/opt/tsm-chandelier/src")
from chand.signals_core import build_signal_frame

SINCE_MS = int(datetime(2026, 8, 10, tzinfo=timezone.utc).timestamp() * 1000)
UNTIL_MS = int(datetime.now(timezone.utc).timestamp() * 1000)
TF_MS = 3_600_000
DB = "/var/lib/botsgeneral/shared_candles.db"


def utc(ms: int) -> str:
    return datetime.fromtimestamp(ms / 1000, timezone.utc).isoformat()


def fetch_binance(symbol: str, start_ms: int, end_ms: int) -> pd.DataFrame:
    rows = []
    cursor = start_ms
    while cursor < end_ms:
        url = (
            f"https://fapi.binance.com/fapi/v1/klines?symbol={symbol}"
            f"&interval=1h&startTime={cursor}&endTime={end_ms}&limit=1500"
        )
        with urllib.request.urlopen(url, timeout=20) as resp:
            raw = json.loads(resp.read().decode("utf-8"))
        if not raw:
            break
        for k in raw:
            ts = int(k[0])
            if ts >= end_ms:
                continue
            rows.append(
                {
                    "ts_ms": ts,
                    "open": float(k[1]),
                    "high": float(k[2]),
                    "low": float(k[3]),
                    "close": float(k[4]),
                    "volume": float(k[5]),
                }
            )
        nxt = int(raw[-1][0]) + TF_MS
        if nxt <= cursor:
            break
        cursor = nxt
    return pd.DataFrame(rows).drop_duplicates("ts_ms").sort_values("ts_ms").reset_index(drop=True)


def load_db(symbol: str, start_ms: int, end_ms: int) -> pd.DataFrame:
    con = sqlite3.connect(f"file:{DB}?mode=ro", uri=True)
    rows = con.execute(
        "SELECT ts_ms,open,high,low,close,volume FROM candles "
        "WHERE exchange=? AND symbol=? AND timeframe=? AND ts_ms>=? AND ts_ms<? ORDER BY ts_ms",
        ("binance", symbol, "1h", start_ms, end_ms),
    ).fetchall()
    con.close()
    return pd.DataFrame(rows, columns=["ts_ms", "open", "high", "low", "close", "volume"])


def sigs(df: pd.DataFrame) -> list[dict]:
    if df.empty or len(df) < 60:
        return []
    feat = build_signal_frame(df)
    out = []
    for i in range(len(feat)):
        ts = int(feat["ts_ms"].iloc[i])
        if ts < SINCE_MS or ts >= UNTIL_MS:
            continue
        long_i = bool(feat["long_signal"].iloc[i])
        short_i = bool(feat["short_signal"].iloc[i])
        if long_i == short_i:
            continue
        out.append(
            {
                "signal_utc": utc(ts),
                "entry_utc": utc(ts + TF_MS),
                "side": "long" if long_i else "short",
                "close": float(feat["close"].iloc[i]),
                "stop": float(feat["stop_price"].iloc[i]),
                "target": float(feat["target_price"].iloc[i]),
            }
        )
    return out


def gaps(df: pd.DataFrame) -> list[dict]:
    out = []
    ts = df["ts_ms"].to_numpy() if len(df) else []
    for a, b in zip(ts[:-1], ts[1:]):
        if int(b) - int(a) != TF_MS:
            out.append({"from": utc(int(a)), "to": utc(int(b)), "missing_h": int((b - a) // TF_MS) - 1})
    return out


def main() -> None:
    start = SINCE_MS - 80 * TF_MS
    for sym in ("BTCUSDT", "ETHUSDT", "SOLUSDT"):
        complete = fetch_binance(sym, start, UNTIL_MS)
        db = load_db(sym, start, UNTIL_MS)
        print("===", sym, "===")
        print("complete_n", len(complete), "db_n", len(db), "db_gaps", gaps(db))
        print("complete_signals", json.dumps(sigs(complete)))
        print("db_signals     ", json.dumps(sigs(db)))


if __name__ == "__main__":
    main()
