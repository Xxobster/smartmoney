from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tradesim.ensure_source import prefer_botsgeneral_tradesim

prefer_botsgeneral_tradesim()

from strategies.common.h0_baseline import run_h0_matrix
from strategies.krown_rsi_momentum_burst.signals import (
    STRATEGY_ID,
    STRATEGY_VERSION,
    build_signal_frame,
    to_tradesim_signals,
)

SYMBOLS = ("BTCUSDT", "ETHUSDT")
TIMEFRAMES = ("1h",)
HOLDS = {"1h": 24}


def main() -> None:
    out_dir = ROOT / "artifacts" / "reports" / "krown_rsi_momentum_burst"
    out_dir.mkdir(parents=True, exist_ok=True)
    print(
        "=== krown_rsi_momentum_burst H0 ===\n"
        "Maximum earned readiness: LIVE_STOP / RESEARCH_ONLY\n"
        "Source side: long_only (+ separate short_mirror)\n"
    )
    results = run_h0_matrix(
        strategy_id=STRATEGY_ID,
        strategy_version=STRATEGY_VERSION,
        symbols=SYMBOLS,
        timeframes=TIMEFRAMES,
        holds=HOLDS,
        build_signal_frame=build_signal_frame,
        to_tradesim_signals=to_tradesim_signals,
        source_side="long_only",
        test_opposite_mirror=True,
    )
    for m in results:
        print(
            f"  {m.get('symbol')} {m.get('timeframe')} {m.get('report_side')}: "
            f"n={m.get('n_trades')} PF={m.get('profit_factor')} "
            f"WR={m.get('win_rate')} pnl={m.get('net_pnl')} status={m.get('status')}"
        )
    path = out_dir / "baseline_h0.json"
    path.write_text(json.dumps(results, indent=2, default=str), encoding="utf-8")
    print("Wrote", path)


if __name__ == "__main__":
    main()
