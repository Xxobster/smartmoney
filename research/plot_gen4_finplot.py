"""Open finplot for frozen Gen4 over a 4-month window (research DB, BTC then ETH)."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd

from engine.data_loader import load_funding, research_db
from engine.features import compute_mtf_features
from engine.tradesim_adapter import (
    PROJECT_STARTING_EQUITY_USDT,
    df_to_barseries,
    features_to_signals,
)
from llm.schema import StrategySpec
from paths import DATASETS
from tradesim import run_backtest


def funding_arrays(symbol: str):
    df = load_funding(DATASETS / "funding.sqlite", symbol)
    if df.empty:
        return None, None
    return (
        df["funding_time_ms"].to_numpy("int64"),
        df["funding_rate"].to_numpy(float),
    )


def load_frozen_spec() -> StrategySpec:
    oos = json.loads(Path("artifacts/reports/gen4_oos_summary.json").read_text(encoding="utf-8"))
    return StrategySpec(**{k: v for k, v in oos["spec"].items() if k in StrategySpec.model_fields})


def run_symbol(symbol: str, start_ms: int, end_ms: int, *, plot: bool) -> None:
    spec = load_frozen_spec()
    print(f"\n=== Gen4 finplot {symbol} {pd.to_datetime(start_ms, unit='ms', utc=True)} -> {pd.to_datetime(end_ms, unit='ms', utc=True)} ===")
    print(f"spec={spec.name} session={spec.session_mode} OB={spec.require_order_block}")

    # Warm-up margin for HTF/swings (30 days before plot window)
    warm_ms = start_ms - 30 * 86_400_000
    feat_full = compute_mtf_features(
        research_db(),
        symbol,
        spec.to_confluence_config(),
        bias_tf=spec.bias_timeframe,
        structure_tf=spec.structure_timeframe,
        execution_tf=spec.execution_timeframe,
        start_ms=warm_ms,
        end_ms=end_ms,
    )
    # Keep warm-up for causal event lookback, but only trade/plot inside the 4 months
    feat = feat_full[(feat_full["ts_ms"] >= start_ms) & (feat_full["ts_ms"] < end_ms)].reset_index(drop=True)
    if "htf_order_flow" in feat.columns:
        feat["long_signal"] = feat["long_signal"] & (feat["htf_order_flow"].fillna(0) >= 0)
        feat["short_signal"] = feat["short_signal"] & (feat["htf_order_flow"].fillna(0) <= 0)

    bars = df_to_barseries(feat, spec.execution_timeframe, symbol)
    signals = features_to_signals(
        feat,
        symbol,
        target_rr=float(spec.target_rr),
        stop_beyond_sweep_atr_mult=float(spec.stop_beyond_sweep_atr_mult),
        use_pd_targets=bool(spec.use_pd_targets),
        max_hold_bars=int(spec.max_hold_bars),
    )
    fts, fr = funding_arrays(symbol)
    print(f"bars={len(feat)} signals={len(signals)} — opening finplot (close window to continue)...")
    bundle = run_backtest(
        strategy_id=f"gen4_finplot_{symbol}",
        strategy_version="gen4",
        bars=bars,
        symbol=symbol,
        signals=signals,
        funding_ts_ms=fts,
        funding_rate=fr,
        starting_equity=PROJECT_STARTING_EQUITY_USDT,
        plot=plot,
        print_headline=True,
        store_path=None,
    )
    m = bundle.metrics
    print(f"{symbol}: trades={m.n_trades} net={m.net_pnl:.2f} pf={m.profit_factor:.4f} exp={m.expectancy:.4f}")


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--symbols", nargs="+", default=["BTCUSDT", "ETHUSDT"])
    p.add_argument("--months", type=int, default=4)
    p.add_argument("--end", default="2026-04-19", help="UTC end date (exclusive-ish end of research OOS)")
    p.add_argument("--no-plot", action="store_true")
    args = p.parse_args()

    end = pd.Timestamp(args.end, tz="UTC")
    start = end - pd.DateOffset(months=args.months)
    start_ms = int(start.timestamp() * 1000)
    end_ms = int(end.timestamp() * 1000)
    print(f"Window: {start.isoformat()} -> {end.isoformat()} ({args.months} months)")

    for sym in args.symbols:
        run_symbol(sym, start_ms, end_ms, plot=not args.no_plot)


if __name__ == "__main__":
    main()
