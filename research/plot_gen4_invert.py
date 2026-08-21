"""Invert Gen4: flip each base trade's side and swap stop/target (same geometry).

Finplot + full tradesim headlines for BTCUSDT and ETHUSDT over the 4-month window.
"""
from __future__ import annotations

import argparse
import json
from dataclasses import replace
from pathlib import Path

import numpy as np
import pandas as pd

from engine.data_loader import load_funding, research_db
from engine.features import compute_mtf_features
from engine.tradesim_adapter import (
    PROJECT_STARTING_EQUITY_USDT,
    df_to_barseries,
    features_to_signals,
)
from llm.schema import StrategySpec
from paths import DATASETS, REPORTS
from smc.confluence import score_confluence
from tradesim import Signal, run_backtest


def load_frozen_spec() -> StrategySpec:
    oos = json.loads(Path("artifacts/reports/gen4_oos_summary.json").read_text(encoding="utf-8"))
    return StrategySpec(**{k: v for k, v in oos["spec"].items() if k in StrategySpec.model_fields})


def funding_arrays(symbol: str):
    df = load_funding(DATASETS / "funding.sqlite", symbol)
    if df.empty:
        return None, None
    return df["funding_time_ms"].to_numpy(np.int64), df["funding_rate"].to_numpy(float)


def prepare_feat(symbol: str, spec: StrategySpec, start_ms: int, end_ms: int) -> pd.DataFrame:
    feat = compute_mtf_features(
        research_db(),
        symbol,
        spec.to_confluence_config(),
        bias_tf=spec.bias_timeframe,
        structure_tf=spec.structure_timeframe,
        execution_tf=spec.execution_timeframe,
        end_ms=end_ms,
    )
    feat = feat[(feat["ts_ms"] >= start_ms) & (feat["ts_ms"] < end_ms)].copy()
    scored = score_confluence(feat, spec.to_confluence_config())
    for col in scored.columns:
        feat[col] = scored[col].to_numpy()
    if "htf_order_flow" in feat.columns:
        feat["long_signal"] = feat["long_signal"] & (feat["htf_order_flow"].fillna(0) >= 0)
        feat["short_signal"] = feat["short_signal"] & (feat["htf_order_flow"].fillna(0) <= 0)
    return feat.reset_index(drop=True)


def invert_signals(signals: list[Signal]) -> list[Signal]:
    """Buy<->sell: flip side and swap stop/target so geometry stays valid."""
    out: list[Signal] = []
    for s in signals:
        out.append(
            replace(
                s,
                side=-int(s.side),
                stop_price=float(s.target_price) if s.target_price is not None else s.stop_price,
                target_price=float(s.stop_price) if s.stop_price is not None else s.target_price,
                tag=(s.tag or "") + "|invert",
            )
        )
    return out


def metrics_dict(bundle, *, symbol: str, invert: bool) -> dict:
    m = bundle.metrics
    return {
        "symbol": symbol,
        "invert": invert,
        "run_id": bundle.run_id,
        "n_trades": int(m.n_trades),
        "n_longs": int(m.n_longs),
        "n_shorts": int(m.n_shorts),
        "net_pnl": float(m.net_pnl),
        "expectancy": float(m.expectancy),
        "profit_factor": float(m.profit_factor),
        "win_rate": float(m.win_rate),
        "payoff_ratio": float(m.payoff_ratio),
        "sharpe_ann": float(m.sharpe.annualised) if m.sharpe is not None else 0.0,
        "hac_sharpe_ann": float(m.sharpe.hac_annualised) if m.sharpe is not None else 0.0,
        "sortino_ann": float(m.sortino_annualised),
        "max_drawdown_pct": float(m.max_drawdown_pct),
        "max_drawdown": float(m.max_drawdown),
        "fees": float(m.total_fees),
        "slippage": float(m.total_slippage),
        "funding": float(m.total_funding),
        "entry_bar_exit_rate": float(m.entry_bar_exit_rate),
        "avg_hold_bars": float(m.avg_hold_bars),
        "long_pnl": float(m.long_pnl),
        "short_pnl": float(m.short_pnl),
        "exposure": float(m.exposure),
        "n_signals": None,
    }


def run_one(symbol: str, spec: StrategySpec, start_ms: int, end_ms: int, *, invert: bool, plot: bool) -> dict:
    tag = "INVERT" if invert else "BASE"
    print(f"\n=== Gen4 {tag} {symbol} ===", flush=True)
    feat = prepare_feat(symbol, spec, start_ms, end_ms)
    base_signals = features_to_signals(
        feat,
        symbol,
        target_rr=float(spec.target_rr),
        stop_beyond_sweep_atr_mult=float(spec.stop_beyond_sweep_atr_mult),
        use_pd_targets=bool(spec.use_pd_targets),
        max_hold_bars=int(spec.max_hold_bars),
    )
    signals = invert_signals(base_signals) if invert else base_signals
    fts, fr = funding_arrays(symbol)
    bars = df_to_barseries(feat, spec.execution_timeframe, symbol)
    print(f"bars={len(feat)} signals={len(signals)} invert={invert} plot={plot}", flush=True)
    bundle = run_backtest(
        strategy_id=f"gen4_{tag.lower()}_{symbol}",
        strategy_version="gen4_invert" if invert else "gen4_base",
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
    out = metrics_dict(bundle, symbol=symbol, invert=invert)
    out["n_signals"] = len(signals)
    out["headline"] = bundle.headline
    return out


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--symbols", nargs="+", default=["BTCUSDT", "ETHUSDT"])
    p.add_argument("--months", type=int, default=4)
    p.add_argument("--end", default="2026-04-19")
    p.add_argument("--no-plot", action="store_true")
    args = p.parse_args()

    end = pd.Timestamp(args.end, tz="UTC")
    start = end - pd.DateOffset(months=args.months)
    start_ms = int(start.timestamp() * 1000)
    end_ms = int(end.timestamp() * 1000)
    spec = load_frozen_spec()
    print(f"Window: {start.isoformat()} -> {end.isoformat()}")
    print(f"Spec: {spec.name} | invert = flip side + swap stop/target")

    base_rows = []
    inv_rows = []
    for sym in args.symbols:
        base_rows.append(run_one(sym, spec, start_ms, end_ms, invert=False, plot=False))
        inv_rows.append(run_one(sym, spec, start_ms, end_ms, invert=True, plot=not args.no_plot))

    def pack(rows: list[dict], mode: str) -> dict:
        return {
            "mode": mode,
            "window": f"{start.date()} -> {end.date()}",
            "n_trades": sum(r["n_trades"] for r in rows),
            "net_pnl": sum(r["net_pnl"] for r in rows),
            "mean_expectancy": float(np.mean([r["expectancy"] for r in rows])),
            "mean_pf": float(np.nanmean([r["profit_factor"] for r in rows])),
            "mean_sharpe_ann": float(np.nanmean([r["sharpe_ann"] for r in rows])),
            "mean_win_rate": float(np.mean([r["win_rate"] for r in rows])),
            "total_fees": sum(r["fees"] for r in rows),
            "per_symbol": [{k: v for k, v in r.items() if k != "headline"} for r in rows],
        }

    summary = {
        "base": pack(base_rows, "BASE (original losing)"),
        "invert": pack(inv_rows, "INVERT (buy<->sell)"),
        "note": (
            "Invert flips Signal.side and swaps stop_price/target_price so the same "
            "price levels are used with opposite direction. Not a new search — diagnostic only."
        ),
    }
    path = REPORTS / "gen4_invert_4m_summary.json"
    path.write_text(json.dumps(summary, indent=2, default=str), encoding="utf-8")

    print("\n========== COMPARISON (4 months) ==========")
    for label, block in ("BASE", summary["base"]), ("INVERT", summary["invert"]):
        print(
            f"{label}: n={block['n_trades']} net={block['net_pnl']:.2f} "
            f"mean_pf={block['mean_pf']:.4f} mean_sharpe={block['mean_sharpe_ann']:.3f} "
            f"mean_wr={block['mean_win_rate']:.2%}"
        )
        for r in block["per_symbol"]:
            print(
                f"  {r['symbol']}: n={r['n_trades']} L/S={r['n_longs']}/{r['n_shorts']} "
                f"net={r['net_pnl']:.2f} pf={r['profit_factor']:.4f} wr={r['win_rate']:.2%} "
                f"sharpe={r['sharpe_ann']:.3f} exp={r['expectancy']:.4f} "
                f"entry_bar_exit={r['entry_bar_exit_rate']:.1%} hold={r['avg_hold_bars']:.1f}"
            )
    print(f"wrote {path}")


if __name__ == "__main__":
    main()
