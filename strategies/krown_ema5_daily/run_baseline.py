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
from strategies.krown_ema5_daily.signals import (
    STRATEGY_ID,
    STRATEGY_VERSION,
    build_signal_frame,
    build_signal_frame_papercut,
    to_tradesim_signals,
)

SYMBOLS = ("BTCUSDT", "ETHUSDT")
TIMEFRAMES = ("1d",)
HOLDS = {"1d": 40}


def _run(name: str, builder, out_name: str) -> None:
    out_dir = ROOT / "artifacts" / "reports" / "krown_ema5_daily"
    out_dir.mkdir(parents=True, exist_ok=True)
    print(
        f"=== {name} ===\n"
        "Maximum earned readiness: LIVE_STOP / RESEARCH_ONLY\n"
        "Source side: long_only (+ separate short_mirror)\n"
    )
    results = run_h0_matrix(
        strategy_id=STRATEGY_ID if "papercut" not in name else f"{STRATEGY_ID}_papercut",
        strategy_version=STRATEGY_VERSION,
        symbols=SYMBOLS,
        timeframes=TIMEFRAMES,
        holds=HOLDS,
        build_signal_frame=builder,
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
    path = out_dir / out_name
    path.write_text(json.dumps(results, indent=2, default=str), encoding="utf-8")
    print("Wrote", path)


def main() -> None:
    variant = "h0"
    if len(sys.argv) > 1:
        variant = sys.argv[1]
    if variant == "papercut":
        _run("krown_ema5_daily H0b paper-cut", build_signal_frame_papercut, "baseline_h0_papercut.json")
    else:
        _run("krown_ema5_daily H0", build_signal_frame, "baseline_h0.json")


if __name__ == "__main__":
    main()
