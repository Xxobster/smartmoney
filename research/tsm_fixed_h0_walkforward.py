"""Fixed-H0 nested outer Out-Of-Sample (OOS) for Secret Mindset packages.

No inner search. Preregister YAML → freeze logical_seed → evaluate each outer
test window once → stitch → compare to frozen V2.1 gates.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Callable

import numpy as np
import pandas as pd
import yaml

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tradesim.ensure_source import prefer_botsgeneral_tradesim

prefer_botsgeneral_tradesim()

from engine.data_loader import load_ohlcv, research_db
from engine.tradesim_adapter import PROJECT_STARTING_EQUITY_USDT, df_to_barseries
from engine.walkforward import build_outer_folds, ms_per_bar
from paths import CONFIG_DIR, REPORTS, ensure_artifact_dirs
from research.registry import TrialRegistry
from tradesim import run_backtest


BuildFn = Callable[[pd.DataFrame], pd.DataFrame]
SignalsFn = Callable[[pd.DataFrame, str, int], list]


def _load_yaml(path: Path) -> dict:
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f)


def _load_gates() -> dict:
    with open(CONFIG_DIR / "frozen_gates.yaml", encoding="utf-8") as f:
        return yaml.safe_load(f)


def _file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _metrics_from_bundle(bundle) -> dict:
    m = bundle.metrics
    pnls = np.asarray([float(t.realized_pnl) for t in bundle.result.trades], dtype=float)
    gross_profit = float(pnls[pnls > 0].sum()) if pnls.size else 0.0
    gross_loss = float((-pnls[pnls < 0]).sum()) if pnls.size else 0.0
    return {
        "n_trades": int(m.n_trades),
        "net_pnl": float(m.net_pnl),
        "expectancy": float(m.expectancy),
        "profit_factor": float(m.profit_factor),
        "win_rate": float(m.win_rate),
        "sharpe_ann": float(m.sharpe.annualised) if m.sharpe else 0.0,
        "hac_sharpe_ann": float(m.sharpe.hac_annualised) if m.sharpe else 0.0,
        "max_drawdown": float(m.max_drawdown_pct),
        "gross_profit": gross_profit,
        "gross_loss": gross_loss,
        "total_fees": float(m.total_fees),
        "total_slippage": float(m.total_slippage),
        "total_funding": float(m.total_funding),
    }


def _run_window(
    *,
    bars: pd.DataFrame,
    touch: pd.DataFrame,
    symbol: str,
    timeframe: str,
    test_start_ms: int,
    test_end_ms: int,
    warmup_bars: int,
    max_hold_bars: int,
    build_signal_frame: BuildFn,
    to_tradesim_signals: SignalsFn,
    strategy_id: str,
    strategy_version: str,
) -> dict:
    bar_ms = ms_per_bar(timeframe)
    warmup_ms = int(warmup_bars) * bar_ms
    feat_start = int(test_start_ms) - warmup_ms
    window = bars[(bars["ts_ms"] >= feat_start) & (bars["ts_ms"] < int(test_end_ms))].copy()
    if window.empty:
        return {
            "n_trades": 0,
            "net_pnl": 0.0,
            "expectancy": 0.0,
            "profit_factor": float("nan"),
            "win_rate": 0.0,
            "sharpe_ann": 0.0,
            "hac_sharpe_ann": 0.0,
            "max_drawdown": 0.0,
            "gross_profit": 0.0,
            "gross_loss": 0.0,
            "status": "empty_window",
        }
    feat = build_signal_frame(window.reset_index(drop=True))
    mask = feat["ts_ms"].to_numpy(np.int64) < int(test_start_ms)
    feat.loc[mask, "long_signal"] = False
    feat.loc[mask, "short_signal"] = False
    sim = feat[feat["ts_ms"] >= int(test_start_ms)].reset_index(drop=True)
    if sim.empty:
        return {
            "n_trades": 0,
            "net_pnl": 0.0,
            "expectancy": 0.0,
            "profit_factor": float("nan"),
            "win_rate": 0.0,
            "sharpe_ann": 0.0,
            "hac_sharpe_ann": 0.0,
            "max_drawdown": 0.0,
            "gross_profit": 0.0,
            "gross_loss": 0.0,
            "status": "empty_test",
        }
    signals = to_tradesim_signals(sim, symbol, max_hold_bars)
    if not signals:
        return {
            "n_trades": 0,
            "net_pnl": 0.0,
            "expectancy": 0.0,
            "profit_factor": float("nan"),
            "win_rate": 0.0,
            "sharpe_ann": 0.0,
            "hac_sharpe_ann": 0.0,
            "max_drawdown": 0.0,
            "gross_profit": 0.0,
            "gross_loss": 0.0,
            "status": "no_signals",
        }
    touch_slice = touch
    if not touch.empty:
        touch_slice = touch[
            (touch["ts_ms"] >= int(test_start_ms) - bar_ms) & (touch["ts_ms"] < int(test_end_ms) + bar_ms)
        ]
    bundle = run_backtest(
        strategy_id=f"{strategy_id}_{symbol.lower()}_{timeframe}_oos",
        strategy_version=strategy_version,
        bars=df_to_barseries(sim, timeframe, symbol),
        symbol=symbol,
        signals=signals,
        touch_bars=df_to_barseries(touch_slice, "1m", symbol) if not touch_slice.empty else None,
        starting_equity=PROJECT_STARTING_EQUITY_USDT,
        plot=False,
        print_headline=False,
        report=False,
        store_path=None,
    )
    out = _metrics_from_bundle(bundle)
    out["status"] = "ok"
    out["n_signals"] = len(signals)
    return out


def run_fixed_h0_walkforward(
    *,
    config_path: Path,
    build_signal_frame: BuildFn,
    to_tradesim_signals: SignalsFn,
    report_subdir: str,
) -> dict:
    ensure_artifact_dirs()
    cfg = _load_yaml(config_path)
    gates = _load_gates()
    hist = gates["historical_oos"]
    risk = gates["risk"]

    symbols = list(cfg["symbols_primary"])
    timeframe = str(cfg["execution_timeframe"])
    warmup_bars = int(cfg.get("warmup_bars", 200))
    max_hold_bars = int(cfg.get("max_hold_bars", 48))
    seed = dict(cfg["logical_seed"])
    root_seed = int(cfg["root_random_seed"])
    strategy_id = str(seed["strategy_id"])
    strategy_version = str(seed.get("strategy_version", "0.1.0"))

    registry = TrialRegistry()
    cfg_hash = _file_sha256(config_path)
    registry.log_event(
        "preregister",
        {
            "generation_id": cfg["generation_id"],
            "config_path": str(config_path),
            "config_sha256": cfg_hash,
            "trial_budget_total": cfg.get("trial_budget_total"),
            "logical_seed": seed,
            "outer_folds": cfg["outer_folds"],
        },
    )
    params_hash = registry.freeze_candidate(
        seed,
        selection_basis=(
            f"fixed_H0_preregistered; generation={cfg['generation_id']}; "
            f"trial_budget=1; no_inner_search; no_tp_sl_grid; config_sha256={cfg_hash[:16]}"
        ),
        code_version=strategy_version,
    )
    registry.log_trial(
        root_seed=root_seed,
        stage="tsm_fixed_h0_freeze",
        params=seed,
        status="frozen",
        proposal_source="preregistered_yaml",
        notes=f"params_hash={params_hash}",
    )

    db = research_db()
    sample = load_ohlcv(db, symbols[0], timeframe)
    if sample.empty:
        raise SystemExit(f"no data for {symbols[0]} {timeframe}")
    outer = build_outer_folds(
        int(sample["ts_ms"].min()),
        int(sample["ts_ms"].max()),
        timeframe,
        cfg,
    )
    print(f"generation={cfg['generation_id']} folds={len(outer)} tf={timeframe} symbols={symbols}")
    print(f"frozen params_hash={params_hash}")

    fold_summaries = []
    per_symbol_fold: dict[str, list[dict]] = {s: [] for s in symbols}
    cache_bars = {s: load_ohlcv(db, s, timeframe) for s in symbols}
    cache_touch = {s: load_ohlcv(db, s, "1m") for s in symbols}

    for fold in outer:
        fold_trades = 0
        fold_pnl = 0.0
        fold_gp = 0.0
        fold_gl = 0.0
        for sym in symbols:
            m = _run_window(
                bars=cache_bars[sym],
                touch=cache_touch[sym],
                symbol=sym,
                timeframe=timeframe,
                test_start_ms=fold.test_start_ms,
                test_end_ms=fold.test_end_ms,
                warmup_bars=warmup_bars,
                max_hold_bars=max_hold_bars,
                build_signal_frame=build_signal_frame,
                to_tradesim_signals=to_tradesim_signals,
                strategy_id=strategy_id,
                strategy_version=strategy_version,
            )
            registry.log_trial(
                root_seed=root_seed,
                stage="tsm_fixed_h0_outer_oos",
                params=seed,
                status="evaluated_once",
                fold_id=fold.fold_id,
                symbol=sym,
                proposal_source="frozen_h0",
                metrics=m,
            )
            per_symbol_fold[sym].append({"fold_id": fold.fold_id, **m})
            fold_trades += int(m.get("n_trades", 0))
            fold_pnl += float(m.get("net_pnl", 0.0))
            fold_gp += float(m.get("gross_profit", 0.0))
            fold_gl += float(m.get("gross_loss", 0.0))
            print(
                f"  fold {fold.fold_id} {sym}: n={m.get('n_trades')} "
                f"PF={m.get('profit_factor')} pnl={m.get('net_pnl'):.2f} status={m.get('status')}"
            )
        eligible = fold_trades >= int(hist["min_resolved_trades_per_gating_fold"])
        fold_summaries.append(
            {
                "fold_id": fold.fold_id,
                "n_trades": fold_trades,
                "net_pnl": fold_pnl,
                "gross_profit": fold_gp,
                "gross_loss": fold_gl,
                "eligible": eligible,
                "positive": fold_pnl > 0,
                "pf_fold": (fold_gp / fold_gl) if fold_gl > 0 else (float("inf") if fold_gp > 0 else float("nan")),
                "test_start_ms": fold.test_start_ms,
                "test_end_ms": fold.test_end_ms,
                "test_start_utc": pd.Timestamp(fold.test_start_ms, unit="ms", tz="UTC").isoformat(),
                "test_end_utc": pd.Timestamp(fold.test_end_ms, unit="ms", tz="UTC").isoformat(),
            }
        )

    # Stitched OOS = concatenate per-symbol fold windows and re-sim once (honest pooled PF / Sharpe)
    stitched_metrics = []
    for sym in symbols:
        parts = []
        for fold in outer:
            bar_ms = ms_per_bar(timeframe)
            warmup_ms = warmup_bars * bar_ms
            feat_start = fold.test_start_ms - warmup_ms
            window = cache_bars[sym][
                (cache_bars[sym]["ts_ms"] >= feat_start) & (cache_bars[sym]["ts_ms"] < fold.test_end_ms)
            ].copy()
            if window.empty:
                continue
            feat = build_signal_frame(window.reset_index(drop=True))
            mask = feat["ts_ms"].to_numpy(np.int64) < fold.test_start_ms
            feat.loc[mask, "long_signal"] = False
            feat.loc[mask, "short_signal"] = False
            sim = feat[feat["ts_ms"] >= fold.test_start_ms].copy()
            parts.append(sim)
        if not parts:
            continue
        stitched = pd.concat(parts, ignore_index=True).drop_duplicates(subset=["ts_ms"]).sort_values("ts_ms")
        stitched = stitched.reset_index(drop=True)
        signals = to_tradesim_signals(stitched, sym, max_hold_bars)
        if not signals:
            stitched_metrics.append(
                {
                    "symbol": sym,
                    "n_trades": 0,
                    "net_pnl": 0.0,
                    "gross_profit": 0.0,
                    "gross_loss": 0.0,
                    "expectancy": 0.0,
                    "sharpe_ann": 0.0,
                    "hac_sharpe_ann": 0.0,
                    "max_drawdown": 0.0,
                    "win_rate": 0.0,
                    "profit_factor": float("nan"),
                }
            )
            continue
        # Touch for full OOS span
        t0 = int(stitched["ts_ms"].min())
        t1 = int(stitched["ts_ms"].max()) + ms_per_bar(timeframe)
        touch = cache_touch[sym]
        touch_slice = touch[(touch["ts_ms"] >= t0) & (touch["ts_ms"] < t1)] if not touch.empty else touch
        bundle = run_backtest(
            strategy_id=f"{strategy_id}_{sym.lower()}_{timeframe}_stitched_oos",
            strategy_version=strategy_version,
            bars=df_to_barseries(stitched, timeframe, sym),
            symbol=sym,
            signals=signals,
            touch_bars=df_to_barseries(touch_slice, "1m", sym) if not touch_slice.empty else None,
            starting_equity=PROJECT_STARTING_EQUITY_USDT,
            plot=False,
            print_headline=True,
            report=False,
            store_path=None,
        )
        mm = _metrics_from_bundle(bundle)
        mm["symbol"] = sym
        stitched_metrics.append(mm)

    gross_profit = float(sum(float(m.get("gross_profit", 0.0) or 0.0) for m in stitched_metrics))
    gross_loss = float(sum(float(m.get("gross_loss", 0.0) or 0.0) for m in stitched_metrics))
    if gross_loss > 0:
        pooled_pf = gross_profit / gross_loss
    elif gross_profit > 0:
        pooled_pf = float("inf")
    else:
        pooled_pf = float("nan")
    stitched_trades = int(sum(int(m.get("n_trades", 0)) for m in stitched_metrics))
    net_pnl = float(sum(float(m.get("net_pnl", 0.0)) for m in stitched_metrics))
    if stitched_trades > 0:
        expectancy = float(
            sum(float(m.get("expectancy", 0.0) or 0.0) * int(m.get("n_trades", 0)) for m in stitched_metrics)
            / stitched_trades
        )
        win_rate = float(
            sum(float(m.get("win_rate", 0.0) or 0.0) * int(m.get("n_trades", 0)) for m in stitched_metrics)
            / stitched_trades
        )
    else:
        expectancy = 0.0
        win_rate = 0.0
    sharpe = float(np.nanmean([m.get("sharpe_ann", np.nan) for m in stitched_metrics])) if stitched_metrics else 0.0
    hac = float(np.nanmean([m.get("hac_sharpe_ann", np.nan) for m in stitched_metrics])) if stitched_metrics else 0.0
    mdd = float(np.nanmax([m.get("max_drawdown", 0.0) for m in stitched_metrics])) if stitched_metrics else 0.0

    eligible = [f for f in fold_summaries if f["eligible"]]
    pos_frac = float(np.mean([1.0 if f["positive"] else 0.0 for f in eligible])) if eligible else 0.0

    checks = {
        "min_complete_outer_folds": bool(len(outer) >= hist["min_complete_outer_folds"]),
        "min_pooled_trades": bool(stitched_trades >= hist["min_pooled_resolved_trades"]),
        "net_pnl_positive": bool(net_pnl > 0),
        "expectancy_positive": bool(expectancy > 0),
        "pooled_pf": bool(pooled_pf == pooled_pf and pooled_pf >= hist["pooled_pf_min"]),
        "sharpe": bool(sharpe >= hist["annualized_daily_mtm_sharpe_min"]),
        "hac_sharpe": bool(hac >= hist["hac_annualized_sharpe_min"]),
        "positive_fold_frac": bool(pos_frac >= hist["positive_eligible_fold_fraction_min"]),
        "mdd": bool(mdd <= risk["baseline_mtm_mdd_max"]),
    }
    # Incomplete Gate B: DSR/bootstrap/PBO/stress not computed here → cannot claim SHADOW_READY
    if stitched_trades < hist["min_pooled_resolved_trades"] or len(eligible) < hist["min_complete_outer_folds"]:
        readiness = "LIVE_STOP / SPARSE_OR_INSUFFICIENT_EVIDENCE"
    elif all(checks.values()):
        readiness = "LIVE_STOP / RESEARCH_ONLY_PENDING_DSR_BOOTSTRAP_STRESS"
    else:
        readiness = "LIVE_STOP / RESEARCH_ONLY_FAILED_GATES"

    principal = next((k for k, v in checks.items() if not v), None)
    if readiness.endswith("PENDING_DSR_BOOTSTRAP_STRESS"):
        principal = principal or "dsr_bootstrap_stress_not_run"

    summary = {
        "maximum_earned_readiness": readiness,
        "evidence_class": "nested_outer_oos_stitched_tradesim_RESEARCH_PROXY",
        "generation_id": cfg["generation_id"],
        "config_path": str(config_path),
        "config_sha256": cfg_hash,
        "params_hash": params_hash,
        "timeframe": timeframe,
        "symbols": symbols,
        "n_outer_folds": len(outer),
        "n_eligible_folds": len(eligible),
        "pooled_trades": stitched_trades,
        "net_pnl": net_pnl,
        "expectancy": expectancy,
        "win_rate_trade_weighted": win_rate,
        "pooled_pf": pooled_pf,
        "gross_profit": gross_profit,
        "gross_loss": gross_loss,
        "sharpe_daily_ann_mean_symbols": sharpe,
        "hac_sharpe_ann_mean_symbols": hac,
        "max_drawdown": mdd,
        "positive_eligible_fold_fraction": pos_frac,
        "checks": checks,
        "principal_blocker": principal,
        "fold_summaries": fold_summaries,
        "per_symbol_fold": per_symbol_fold,
        "stitched_metrics": stitched_metrics,
        "gate_note": (
            "Partial Gate B mechanical checks only. DSR, dependence-aware bootstrap, "
            "PBO, and cost-stress not run — SHADOW_READY cannot be earned from this script alone."
        ),
        "trial_budget_total": cfg.get("trial_budget_total"),
        "full_history_baselines_are_not_selection_evidence": True,
    }

    registry.log_event("tsm_fixed_h0_oos_complete", summary)
    registry.close()

    out_dir = REPORTS / report_subdir
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"{timeframe}_oos_summary.json"
    out_path.write_text(json.dumps(summary, indent=2, default=str), encoding="utf-8")
    sitrep = out_dir / f"{timeframe}_oos_sitrep.md"
    sitrep.write_text(
        "\n".join(
            [
                f"# Sitrep — {cfg['generation_id']}",
                "",
                f"- **Maximum earned readiness:** `{readiness}`",
                f"- **Evidence class:** nested outer OOS stitched · `RESEARCH_PROXY`",
                f"- **Principal blocker:** `{principal}`",
                f"- **Pooled OOS trades:** {stitched_trades}",
                f"- **Pooled PF:** {pooled_pf}",
                f"- **Net PnL:** {net_pnl}",
                f"- **Sharpe ann (mean symbols):** {sharpe}",
                f"- **HAC Sharpe ann:** {hac}",
                f"- **Eligible folds:** {len(eligible)} / {len(outer)} (positive frac {pos_frac:.2f})",
                f"- **Config hash:** `{cfg_hash[:16]}…`",
                f"- **Params hash:** `{params_hash[:16]}…`",
                "",
                "## Checks",
                "",
                *[f"- `{k}`: `{v}`" for k, v in checks.items()],
                "",
                "## Fold summaries",
                "",
                *[
                    f"- fold {f['fold_id']}: n={f['n_trades']} pnl={f['net_pnl']:.2f} "
                    f"eligible={f['eligible']} positive={f['positive']} "
                    f"({f['test_start_utc'][:10]} → {f['test_end_utc'][:10]})"
                    for f in fold_summaries
                ],
                "",
            ]
        ),
        encoding="utf-8",
    )
    print("Wrote", out_path)
    print("Wrote", sitrep)
    print("READINESS", readiness, "blocker", principal, "pooled_pf", pooled_pf, "trades", stitched_trades)
    return summary


def main_pressure_zone() -> None:
    from strategies.tsm_pressure_zone.signals import build_signal_frame, to_tradesim_signals

    run_fixed_h0_walkforward(
        config_path=CONFIG_DIR / "search_space_tsm_pressure_zone_1d.yaml",
        build_signal_frame=build_signal_frame,
        to_tradesim_signals=to_tradesim_signals,
        report_subdir="tsm_pressure_zone",
    )


def main_heikin() -> None:
    from strategies.tsm_heikin_ashi_ema50.signals import build_signal_frame, to_tradesim_signals

    run_fixed_h0_walkforward(
        config_path=CONFIG_DIR / "search_space_tsm_heikin_ashi_ema50_1h.yaml",
        build_signal_frame=build_signal_frame,
        to_tradesim_signals=to_tradesim_signals,
        report_subdir="tsm_heikin_ashi_ema50",
    )


def main_impulse_volume() -> None:
    from strategies.tsm_impulse_volume.signals import build_signal_frame, to_tradesim_signals

    run_fixed_h0_walkforward(
        config_path=CONFIG_DIR / "search_space_tsm_impulse_volume_4h.yaml",
        build_signal_frame=build_signal_frame,
        to_tradesim_signals=to_tradesim_signals,
        report_subdir="tsm_impulse_volume",
    )


def main_engulf_demand() -> None:
    from strategies.tsm_engulf_demand.signals import build_signal_frame, to_tradesim_signals

    run_fixed_h0_walkforward(
        config_path=CONFIG_DIR / "search_space_tsm_engulf_demand_4h.yaml",
        build_signal_frame=build_signal_frame,
        to_tradesim_signals=to_tradesim_signals,
        report_subdir="tsm_engulf_demand",
    )


def main_chandelier() -> None:
    from strategies.tsm_chandelier.signals import build_signal_frame, to_tradesim_signals

    run_fixed_h0_walkforward(
        config_path=CONFIG_DIR / "search_space_tsm_chandelier_1h.yaml",
        build_signal_frame=build_signal_frame,
        to_tradesim_signals=to_tradesim_signals,
        report_subdir="tsm_chandelier",
    )


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "which",
        choices=(
            "pressure_zone_1d",
            "heikin_ashi_1h",
            "impulse_volume_4h",
            "engulf_demand_4h",
            "chandelier_1h",
            "both",
        ),
    )
    args = ap.parse_args()
    if args.which in ("pressure_zone_1d", "both"):
        main_pressure_zone()
    if args.which in ("heikin_ashi_1h", "both"):
        main_heikin()
    if args.which == "impulse_volume_4h":
        main_impulse_volume()
    if args.which == "engulf_demand_4h":
        main_engulf_demand()
    if args.which == "chandelier_1h":
        main_chandelier()




if __name__ == "__main__":
    main()
