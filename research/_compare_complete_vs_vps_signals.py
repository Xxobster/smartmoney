#!/usr/bin/env python3
"""Compare chandelier signals: complete Binance 1h vs gapped VPS shared series."""

from __future__ import annotations

import json
import sys
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from strategies.tsm_chandelier.signals import build_signal_frame

SINCE = datetime(2026, 8, 10, tzinfo=timezone.utc)
UNTIL = datetime.now(timezone.utc)
SINCE_MS = int(SINCE.timestamp() * 1000)
UNTIL_MS = int(UNTIL.timestamp() * 1000)
TF_MS = 3_600_000
VPS = ROOT / "artifacts" / "reports" / "tsm_chandelier" / "vps94_parity_export"
OUT = ROOT / "artifacts" / "reports" / "tsm_chandelier" / "live_vs_complete_binance_signals.json"


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


def sigs(df: pd.DataFrame) -> list[dict]:
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
    ts = df["ts_ms"].to_numpy()
    for a, b in zip(ts[:-1], ts[1:]):
        if int(b) - int(a) != TF_MS:
            out.append({"from": utc(int(a)), "to": utc(int(b)), "missing_h": int((b - a) // TF_MS) - 1})
    return out


def main() -> None:
    report = {"since": SINCE.isoformat(), "until": UNTIL.isoformat(), "symbols": {}}
    for sym in ("BTCUSDT", "ETHUSDT", "SOLUSDT"):
        complete = fetch_binance(sym, SINCE_MS - 80 * TF_MS, UNTIL_MS)
        vps = pd.read_csv(VPS / f"{sym}_1h_binance.csv")
        vps = vps[(vps["ts_ms"] >= SINCE_MS - 80 * TF_MS) & (vps["ts_ms"] < UNTIL_MS)].copy()
        report["symbols"][sym] = {
            "complete_n": int(len(complete)),
            "vps_n": int(len(vps)),
            "vps_gaps_in_window": gaps(vps.sort_values("ts_ms")),
            "complete_signals": sigs(complete),
            "vps_gapped_signals": sigs(vps.sort_values("ts_ms")),
        }
        print(sym, "complete", len(complete), "vps", len(vps), "gaps", report["symbols"][sym]["vps_gaps_in_window"])
        print("  complete signals", report["symbols"][sym]["complete_signals"])
        print("  vps signals     ", report["symbols"][sym]["vps_gapped_signals"])
    OUT.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print("Wrote", OUT)


if __name__ == "__main__":
    main()
