"""Post-hoc DSR + bootstrap for frozen Gen4 (does not retune)."""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

from engine.data_loader import load_ohlcv, research_db
from engine.metrics import block_bootstrap_positive_expectancy, deflated_sharpe_ratio
from engine.tradesim_adapter import (
    PROJECT_STARTING_EQUITY_USDT,
    df_to_barseries,
    features_to_signals,
)
from engine.walkforward import build_outer_folds
from llm.schema import StrategySpec
from research.run_gen2 import funding_arrays, load_search_cfg, precompute, slice_feat
from smc.confluence import score_confluence
from tradesim import run_backtest


def main() -> None:
    oos = json.loads(Path("artifacts/reports/gen4_oos_summary.json").read_text(encoding="utf-8"))
    search_sum = json.loads(Path("artifacts/reports/gen4_search_summary.json").read_text(encoding="utf-8"))
    spec = StrategySpec(**{k: v for k, v in oos["spec"].items() if k in StrategySpec.model_fields})
    search = load_search_cfg(Path("config/search_space_gen4.yaml"))
    symbols = ["BTCUSDT", "ETHUSDT"]
    cache = {sym: precompute(sym, spec) for sym in symbols}
    sample = load_ohlcv(research_db(), symbols[0], spec.execution_timeframe)
    outer = build_outer_folds(
        int(sample["ts_ms"].min()),
        int(sample["ts_ms"].max()),
        spec.execution_timeframe,
        search,
    )

    all_pnls: list[np.ndarray] = []
    for sym in symbols:
        parts = [slice_feat(cache[sym], fold.test_start_ms, fold.test_end_ms) for fold in outer]
        stitched = pd.concat(parts, ignore_index=True)
        scored = score_confluence(stitched, spec.to_confluence_config())
        for col in scored.columns:
            stitched[col] = scored[col].to_numpy()
        if "htf_order_flow" in stitched.columns:
            stitched["long_signal"] = stitched["long_signal"] & (stitched["htf_order_flow"].fillna(0) >= 0)
            stitched["short_signal"] = stitched["short_signal"] & (stitched["htf_order_flow"].fillna(0) <= 0)
        fts, fr = funding_arrays(sym)
        bars = df_to_barseries(stitched, spec.execution_timeframe, sym)
        signals = features_to_signals(
            stitched,
            sym,
            target_rr=float(spec.target_rr),
            stop_beyond_sweep_atr_mult=float(spec.stop_beyond_sweep_atr_mult),
            use_pd_targets=bool(spec.use_pd_targets),
            max_hold_bars=int(spec.max_hold_bars),
        )
        bundle = run_backtest(
            strategy_id=f"gen4_dsr_{sym}",
            strategy_version="gen4",
            bars=bars,
            symbol=sym,
            signals=signals,
            funding_ts_ms=fts,
            funding_rate=fr,
            starting_equity=PROJECT_STARTING_EQUITY_USDT,
            plot=False,
            print_headline=False,
            store_path=None,
        )
        pnls = np.asarray([float(t.realized_pnl) for t in bundle.result.trades], dtype=float)
        all_pnls.append(pnls)
        print(sym, "n=", len(pnls), "exp=", float(pnls.mean()) if len(pnls) else None, "pf=", bundle.metrics.profit_factor)

    pnls = np.concatenate(all_pnls) if all_pnls else np.array([])
    n_trials = int(search_sum.get("n_trials") or 649)
    sharpe_ann = float(oos["sharpe_daily_ann"])
    n_obs = 900
    dsr = deflated_sharpe_ratio(sharpe_ann, n_obs, n_trials)
    boot = block_bootstrap_positive_expectancy(pnls, n_resamples=10_000, seed=20260727)
    # Approximate cost stress (not a full re-sim): report only
    stress_pf = float(oos["pooled_pf"]) / 1.15
    stress_pnl = float(oos["net_pnl"]) * 0.7
    out = {
        "n_trades": int(len(pnls)),
        "expectancy": float(pnls.mean()) if len(pnls) else 0.0,
        "dsr": dsr,
        "dsr_pass": bool(dsr >= 0.95),
        "bootstrap_pos_exp": boot,
        "bootstrap_pass": bool(boot >= 0.90),
        "approx_stress_pf": stress_pf,
        "approx_stress_pnl": stress_pnl,
        "approx_stress_note": "proxy only (PF/1.15, PnL*0.7); not a full 2x-slip re-sim",
        "n_trials": n_trials,
        "sharpe_ann": sharpe_ann,
        "n_obs_days": n_obs,
        "pbo": None,
        "pbo_status": "PBO_UNAVAILABLE_INSUFFICIENT_MATRIX",
    }
    Path("artifacts/reports/gen4_dsr_bootstrap.json").write_text(json.dumps(out, indent=2), encoding="utf-8")
    print(json.dumps(out, indent=2))


if __name__ == "__main__":
    main()
