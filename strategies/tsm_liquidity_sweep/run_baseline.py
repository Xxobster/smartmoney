"""Baseline RESEARCH_PROXY backtest for TSM liquidity sweep H0 on BTCUSDT/ETHUSDT.

Does NOT claim SHADOW_READY — full-history exploratory only until nested walk-forward
is registered and outer Out-Of-Sample (OOS) is evaluated once.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tradesim.ensure_source import prefer_botsgeneral_tradesim

prefer_botsgeneral_tradesim()

from engine.data_loader import load_ohlcv, research_db
from engine.features import compute_mtf_features
from engine.tradesim_adapter import run_tradesim_on_features
from strategies.tsm_liquidity_sweep.confluence_config import (
    DEFAULT_HTF,
    DEFAULT_LTF,
    DEFAULT_STOP_ATR_MULT,
    DEFAULT_SYMBOLS,
    DEFAULT_TARGET_RR,
    STRATEGY_ID,
    STRATEGY_VERSION,
    TSM_LIQUIDITY_H0,
)


def run_symbol(symbol: str) -> dict:
    db = research_db()
    if not db.exists():
        raise FileNotFoundError(
            f"Research DB missing: {db}. Build with data.build_datasets first."
        )
    feat = compute_mtf_features(
        db,
        symbol,
        TSM_LIQUIDITY_H0,
        bias_tf="4h",
        structure_tf=DEFAULT_HTF,
        execution_tf=DEFAULT_LTF,
    )
    touch = load_ohlcv(db, symbol, "1m")
    metrics = run_tradesim_on_features(
        feat,
        symbol,
        DEFAULT_LTF,
        target_rr=DEFAULT_TARGET_RR,
        stop_beyond_sweep_atr_mult=DEFAULT_STOP_ATR_MULT,
        use_pd_targets=False,  # video RR qualitative; fixed RR for H0
        max_hold_bars=96,
        touch_df=touch if not touch.empty else None,
        touch_timeframe="1m" if not touch.empty else None,
        strategy_id=f"{STRATEGY_ID}_{symbol.lower()}",
        print_headline=True,
    )
    metrics.update(
        {
            "symbol": symbol,
            "ltf": DEFAULT_LTF,
            "htf": DEFAULT_HTF,
            "strategy_id": STRATEGY_ID,
            "strategy_version": STRATEGY_VERSION,
            "readiness": "LIVE_STOP / RESEARCH_ONLY",
            "evidence_class": "RESEARCH_PROXY",
            "note": "Full-history exploratory; not stitched outer-OOS gate evidence.",
        }
    )
    return metrics


def main() -> None:
    out_dir = ROOT / "artifacts" / "reports" / "tsm_liquidity_sweep"
    out_dir.mkdir(parents=True, exist_ok=True)
    results = []
    print("=== tsm_liquidity_sweep H0 baseline ===")
    print("Maximum earned readiness: LIVE_STOP / RESEARCH_ONLY")
    print("Evidence class: RESEARCH_PROXY")
    print("Principal blocker: no nested walk-forward / outer OOS freeze yet\n")
    for sym in DEFAULT_SYMBOLS:
        print(f"--- {sym} ---")
        m = run_symbol(sym)
        results.append(m)
        print(
            f"  n_trades={m.get('n_trades')} PF={m.get('profit_factor')} "
            f"SharpeAnn={m.get('sharpe_ann')} MDD={m.get('max_drawdown')} "
            f"status={m.get('status')}"
        )
    path = out_dir / "baseline_h0.json"
    path.write_text(json.dumps(results, indent=2, default=str), encoding="utf-8")
    print(f"\nWrote {path}")


if __name__ == "__main__":
    main()
