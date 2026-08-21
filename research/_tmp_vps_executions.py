#!/usr/bin/env python3
"""Pull Bybit executions + closed PnL for BTC/ETH (run on VPS). No secrets printed."""
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, "/opt/tsm-chandelier/src")
from chand.live.bybit_client import BybitClient, BybitCredentials  # noqa: E402

KEYS = Path("/opt/tsm-chandelier/config/api_keys.json")
# Most recent first (no startTime) so we capture chandelier live fills, not older account history.
START_MS = None
SYMBOLS = ["BTCUSDT", "ETHUSDT", "SOLUSDT"]


def redact(d):
    out = {}
    for k, v in d.items():
        lk = str(k).lower()
        if any(x in lk for x in ("key", "secret", "token", "sign")):
            continue
        out[k] = v
    return out


creds = BybitCredentials.from_account("Xxobster6", KEYS)
client = BybitClient(creds)
report = {"generated_utc": datetime.now(timezone.utc).isoformat(), "symbols": {}}
for sym in SYMBOLS:
    closed = client.get_closed_pnl(sym, limit=50, start_ms=START_MS)
    execs = client.get_executions(sym, limit=100, start_ms=START_MS)
    report["symbols"][sym] = {
        "closed_pnl": [redact(x) for x in closed],
        "executions": [redact(x) for x in execs],
    }

out = Path("/tmp/vps94_live_executions.json")
out.write_text(json.dumps(report, indent=2, default=str), encoding="utf-8")
print("WROTE", out)
for sym, block in report["symbols"].items():
    print(sym, "closed", len(block["closed_pnl"]), "execs", len(block["executions"]))
    for c in block["closed_pnl"]:
        print(
            "  closed",
            c.get("symbol"),
            "side",
            c.get("side"),
            "entry",
            c.get("avgEntryPrice"),
            "exit",
            c.get("avgExitPrice"),
            "pnl",
            c.get("closedPnl"),
            "openFee",
            c.get("openFee"),
            "closeFee",
            c.get("closeFee"),
            "updated",
            c.get("updatedTime"),
            "execType",
            c.get("execType"),
        )
    for e in block["executions"]:
        print(
            "  exec",
            e.get("execTime"),
            e.get("side"),
            e.get("execType"),
            "px",
            e.get("execPrice"),
            "qty",
            e.get("execQty"),
            "fee",
            e.get("execFee"),
            "feeRate",
            e.get("feeRate"),
            "orderType",
            e.get("orderType"),
            "stopOrderType",
            e.get("stopOrderType"),
        )
