"""Generation 2 research campaign: tradesim engine + Ollama proposals + sparse redesign.

Preregistered in config/search_space_gen2.yaml BEFORE any Gen2 outer OOS.
Do not expand the candidate space after viewing OOS.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Optional

import numpy as np
import optuna
import pandas as pd
import yaml

from tradesim.ensure_source import assert_engine_version

assert_engine_version(require_under=r"C:\projects\botsgeneral\packages\tradesim")

from engine.data_loader import load_funding, load_ohlcv, research_db
from engine.features import compute_mtf_features
from engine.tradesim_adapter import run_tradesim_on_features
from engine.walkforward import build_inner_folds, build_outer_folds, fold_seed
from llm.proposer import StrategyProposer
from llm.schema import StrategySpec
from paths import CONFIG_DIR, DATASETS, REPORTS, ensure_artifact_dirs
from research.registry import TrialRegistry
from smc.confluence import score_confluence

optuna.logging.set_verbosity(optuna.logging.WARNING)


def load_search_cfg(path: Path | None = None) -> dict:
    p = path or (CONFIG_DIR / "search_space_gen2.yaml")
    with open(p, encoding="utf-8") as f:
        return yaml.safe_load(f)


def load_gates() -> dict:
    with open(CONFIG_DIR / "frozen_gates.yaml", encoding="utf-8") as f:
        return yaml.safe_load(f)


def slice_feat(feat: pd.DataFrame, start_ms: int, end_ms: int) -> pd.DataFrame:
    return feat[(feat["ts_ms"] >= start_ms) & (feat["ts_ms"] < end_ms)].reset_index(drop=True)


def funding_arrays(symbol: str):
    df = load_funding(DATASETS / "funding.sqlite", symbol)
    if df.empty:
        return None, None
    return (
        df["funding_time_ms"].to_numpy(np.int64),
        df["funding_rate"].to_numpy(float),
    )


def evaluate_window(
    feat: pd.DataFrame,
    spec: StrategySpec,
    symbol: str,
    start_ms: int,
    end_ms: int,
) -> dict[str, Any]:
    sub = slice_feat(feat, start_ms, end_ms)
    if len(sub) < 50:
        return {"n_trades": 0, "expectancy": -1e9, "net_pnl": 0.0, "status": "insufficient_bars"}
    cfg = spec.to_confluence_config()
    scored = score_confluence(sub, cfg)
    for col in scored.columns:
        sub[col] = scored[col].to_numpy()
    if "htf_order_flow" in sub.columns:
        sub["long_signal"] = sub["long_signal"] & (sub["htf_order_flow"].fillna(0) >= 0)
        sub["short_signal"] = sub["short_signal"] & (sub["htf_order_flow"].fillna(0) <= 0)

    fts, fr = funding_arrays(symbol)
    # Optional 1m touch for 5m decisions — skip if not in research db (not copied by default)
    return run_tradesim_on_features(
        sub,
        symbol,
        spec.execution_timeframe,
        target_rr=float(spec.target_rr),
        stop_beyond_sweep_atr_mult=float(spec.stop_beyond_sweep_atr_mult),
        use_pd_targets=bool(spec.use_pd_targets),
        max_hold_bars=int(spec.max_hold_bars),
        risk_fraction=None,  # tradesim research default = min exchange size
        funding_ts_ms=fts,
        funding_rate=fr,
        strategy_id=f"smc_{spec.name}",
        print_headline=False,
    )


def precompute(symbol: str, seed_spec: StrategySpec) -> pd.DataFrame:
    print(f"  features {symbol} {seed_spec.execution_timeframe}/{seed_spec.structure_timeframe}/{seed_spec.bias_timeframe}...")
    return compute_mtf_features(
        research_db(),
        symbol,
        seed_spec.to_confluence_config(),
        bias_tf=seed_spec.bias_timeframe,
        structure_tf=seed_spec.structure_timeframe,
        execution_tf=seed_spec.execution_timeframe,
    )


def sample_spec(trial: optuna.Trial, base: StrategySpec, space: dict) -> StrategySpec:
    d = base.model_dump()
    for key, choices in space.items():
        if key not in StrategySpec.model_fields:
            continue
        # If base value is outside choices (e.g. LLM said 15m but Gen2 freezes 5m), clamp first
        if d.get(key) not in choices:
            d[key] = choices[0]
        d[key] = trial.suggest_categorical(key, choices)
    d["name"] = f"optuna_{base.name}_{trial.number}"
    if "execution_timeframe" in space:
        d["execution_timeframe"] = space["execution_timeframe"][0]
    return StrategySpec(**{k: v for k, v in d.items() if k in StrategySpec.model_fields})


def run_family(
    family: dict,
    search: dict,
    symbols: list[str],
    registry: TrialRegistry,
    root_seed: int,
    outer_folds,
    optuna_trials: int,
    llm_specs: list[StrategySpec],
) -> dict[str, Any]:
    seed = StrategySpec.from_logical_seed(family["logical_seed"])
    # Attach event_lookback if present
    if "event_lookback" in family["logical_seed"]:
        seed.event_lookback = int(family["logical_seed"]["event_lookback"])
    space = search["search_space"]
    proposals = [seed] + [s for s in llm_specs]
    # Deduplicate by dump
    seen = set()
    uniq = []
    for p in proposals:
        key = json.dumps(p.to_params_dict(), sort_keys=True, default=str)
        if key in seen:
            continue
        seen.add(key)
        uniq.append(p)

    sel_fold = outer_folds[0]
    inner = build_inner_folds(
        sel_fold.train_start_ms,
        sel_fold.train_end_ms,
        seed.execution_timeframe,
        search,
    )
    best = {"score": -1e18, "spec": None, "metrics": None, "family": family["id"]}

    for p_i, prop in enumerate(uniq):
        print(f" Family {family['id']} proposal {p_i}: {prop.name}")
        try:
            cache = {sym: precompute(sym, prop) for sym in symbols}
        except Exception as exc:
            registry.log_trial(
                root_seed=root_seed,
                stage="gen2_feature_fail",
                params=prop.to_params_dict(),
                status="failed",
                proposal_source=family["id"],
                notes=str(exc),
            )
            continue

        def objective(trial: optuna.Trial) -> float:
            spec = sample_spec(trial, prop, space)
            fold_scores = []
            trade_counts = []
            for inf in inner:
                seed_i = fold_seed(root_seed, inf.fold_id, trial.number)
                sym_scores = []
                for sym in symbols:
                    m = evaluate_window(
                        cache[sym],
                        spec,
                        sym,
                        inf.test_start_ms,
                        inf.test_end_ms,
                    )
                    registry.log_trial(
                        root_seed=root_seed,
                        stage="gen2_inner",
                        params=spec.to_params_dict(),
                        status=m.get("status", "ok"),
                        fold_id=inf.fold_id,
                        symbol=sym,
                        proposal_source=family["id"],
                        metrics=m,
                    )
                    # Score: expectancy, with soft preference for enough trades
                    n = int(m.get("n_trades", 0))
                    trade_counts.append(n)
                    e = float(m.get("expectancy", -1e9))
                    if m.get("wallet_blown"):
                        e = -1e6
                    sym_scores.append(e)
                if sym_scores:
                    fold_scores.append(float(np.mean(sym_scores)))
            score = float(np.mean(fold_scores)) if fold_scores else -1e9
            # Soft bonus if median trades/window >= 3 (sample sufficiency pressure)
            if trade_counts and float(np.median(trade_counts)) >= 3:
                score += 0.0  # do not distort expectancy; just record
            trial.set_user_attr("spec", spec.to_params_dict())
            trial.set_user_attr("median_trades", float(np.median(trade_counts)) if trade_counts else 0.0)
            return score

        sampler = optuna.samplers.TPESampler(seed=fold_seed(root_seed, hash(family["id"]) % 1000, p_i))
        study = optuna.create_study(direction="maximize", sampler=sampler)
        enqueue = {}
        for k, choices in space.items():
            if k not in prop.to_params_dict():
                continue
            val = prop.to_params_dict()[k]
            enqueue[k] = val if val in choices else choices[0]
        if enqueue:
            study.enqueue_trial(enqueue)
        study.optimize(objective, n_trials=optuna_trials, show_progress_bar=False)

        if study.best_trial is not None:
            spec_dict = study.best_trial.user_attrs.get("spec")
            score = float(study.best_value)
            registry.log_trial(
                root_seed=root_seed,
                stage="gen2_inner_best",
                params=spec_dict,
                status="candidate",
                proposal_source=family["id"],
                metrics={
                    "inner_mean_expectancy": score,
                    "median_trades": study.best_trial.user_attrs.get("median_trades"),
                },
            )
            if score > best["score"]:
                best = {
                    "score": score,
                    "spec": spec_dict,
                    "metrics": {"inner_mean_expectancy": score},
                    "family": family["id"],
                }
    return best


def evaluate_outer_oos(
    spec_dict: dict,
    search: dict,
    symbols: list[str],
    registry: TrialRegistry,
    root_seed: int,
) -> dict:
    gates = load_gates()
    spec = StrategySpec(**{k: v for k, v in spec_dict.items() if k in StrategySpec.model_fields})
    cache = {sym: precompute(sym, spec) for sym in symbols}
    sample = load_ohlcv(research_db(), symbols[0], spec.execution_timeframe)
    outer = build_outer_folds(
        int(sample["ts_ms"].min()),
        int(sample["ts_ms"].max()),
        spec.execution_timeframe,
        search,
    )
    fold_summaries = []
    all_pnls = []
    sharpes = []
    hacs = []
    mdds = []
    for fold in outer:
        fold_trades = 0
        fold_pnl = 0.0
        for sym in symbols:
            m = evaluate_window(cache[sym], spec, sym, fold.test_start_ms, fold.test_end_ms)
            registry.log_trial(
                root_seed=root_seed,
                stage="gen2_outer_oos",
                params=spec.to_params_dict(),
                status="evaluated_once",
                fold_id=fold.fold_id,
                symbol=sym,
                proposal_source="frozen_gen2",
                metrics=m,
            )
            n = int(m.get("n_trades", 0))
            fold_trades += n
            fold_pnl += float(m.get("net_pnl", 0.0))
            # Approximate per-trade pnl list unavailable; use expectancy*n
            if n > 0:
                all_pnls.extend([float(m.get("expectancy", 0.0))] * n)
            sharpes.append(float(m.get("sharpe_ann", 0.0)))
            hacs.append(float(m.get("hac_sharpe_ann", 0.0)))
            mdds.append(float(m.get("max_drawdown", 0.0)))
        gains = max(fold_pnl, 0.0)
        losses = abs(min(fold_pnl, 0.0))
        # crude fold PF from net only is wrong; mark eligible by trade count
        eligible = fold_trades >= int(gates["historical_oos"]["min_resolved_trades_per_gating_fold"])
        fold_summaries.append(
            {
                "fold_id": fold.fold_id,
                "n_trades": fold_trades,
                "net_pnl": fold_pnl,
                "eligible": eligible,
                "positive": fold_pnl > 0,
                "test_start_ms": fold.test_start_ms,
                "test_end_ms": fold.test_end_ms,
            }
        )

    pooled_trades = int(sum(f["n_trades"] for f in fold_summaries))
    net_pnl = float(sum(f["net_pnl"] for f in fold_summaries))
    eligible = [f for f in fold_summaries if f["eligible"]]
    pos_frac = float(np.mean([1.0 if f["positive"] else 0.0 for f in eligible])) if eligible else 0.0
    # Recompute pooled PF by re-running full stitched OOS once per symbol
    stitched_metrics = []
    for sym in symbols:
        # stitch all outer test windows
        parts = []
        for fold in outer:
            parts.append(slice_feat(cache[sym], fold.test_start_ms, fold.test_end_ms))
        stitched = pd.concat(parts, ignore_index=True) if parts else pd.DataFrame()
        if stitched.empty:
            continue
        scored = score_confluence(stitched, spec.to_confluence_config())
        for col in scored.columns:
            stitched[col] = scored[col].to_numpy()
        if "htf_order_flow" in stitched.columns:
            stitched["long_signal"] = stitched["long_signal"] & (stitched["htf_order_flow"].fillna(0) >= 0)
            stitched["short_signal"] = stitched["short_signal"] & (stitched["htf_order_flow"].fillna(0) <= 0)
        fts, fr = funding_arrays(sym)
        stitched_metrics.append(
            run_tradesim_on_features(
                stitched,
                sym,
                spec.execution_timeframe,
                target_rr=float(spec.target_rr),
                stop_beyond_sweep_atr_mult=float(spec.stop_beyond_sweep_atr_mult),
                use_pd_targets=bool(spec.use_pd_targets),
                max_hold_bars=int(spec.max_hold_bars),
                funding_ts_ms=fts,
                funding_rate=fr,
                strategy_id="smc_gen2_stitched",
                print_headline=True,
            )
        )

    # V2: pooled PF = sum(gross_profit) / sum(|gross_loss|), never mean of per-symbol PFs
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
    # Trade-weighted expectancy across symbols
    if stitched_trades > 0:
        expectancy = float(
            sum(float(m.get("expectancy", 0.0) or 0.0) * int(m.get("n_trades", 0)) for m in stitched_metrics)
            / stitched_trades
        )
    else:
        expectancy = 0.0
    sharpe = float(np.nanmean([m.get("sharpe_ann", np.nan) for m in stitched_metrics])) if stitched_metrics else 0.0
    hac = float(np.nanmean([m.get("hac_sharpe_ann", np.nan) for m in stitched_metrics])) if stitched_metrics else 0.0
    mdd = float(np.nanmax([m.get("max_drawdown", 0.0) for m in stitched_metrics])) if stitched_metrics else 0.0

    hist = gates["historical_oos"]
    risk = gates["risk"]
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
    if stitched_trades < hist["min_pooled_resolved_trades"]:
        readiness = "SPARSE_OR_INSUFFICIENT_EVIDENCE"
    elif all(checks.values()):
        readiness = "SHADOW_READY_CANDIDATE_PENDING_DSR_BOOTSTRAP"
    else:
        readiness = "RESEARCH_ONLY_FAILED_GATES"

    return {
        "readiness": readiness,
        "evidence_class": "nested_outer_oos_stitched_tradesim_RESEARCH_PROXY",
        "generation": search.get("generation_id"),
        "pooled_trades": stitched_trades,
        "fold_trade_sum": pooled_trades,
        "net_pnl": net_pnl,
        "expectancy": expectancy,
        "pooled_pf": pooled_pf,
        "sharpe_daily_ann": sharpe,
        "hac_sharpe_ann": hac,
        "max_drawdown": mdd,
        "positive_eligible_fold_fraction": pos_frac,
        "n_eligible_folds": len(eligible),
        "n_outer_folds": len(outer),
        "checks": checks,
        "fold_summaries": fold_summaries,
        "stitched_metrics": stitched_metrics,
        "principal_blocker": next((k for k, v in checks.items() if not v), None),
        "engine": "tradesim",
    }


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--symbols", nargs="+", default=None)
    p.add_argument("--optuna-trials", type=int, default=None)
    p.add_argument("--llm-proposals", type=int, default=None)
    p.add_argument("--no-llm", action="store_true")
    p.add_argument("--families", nargs="+", default=None, help="Subset of family ids")
    p.add_argument("--config", type=str, default="search_space_gen2.yaml")
    p.add_argument("--report-prefix", type=str, default=None)
    args = p.parse_args()

    ensure_artifact_dirs()
    REPORTS.mkdir(parents=True, exist_ok=True)
    cfg_path = Path(args.config)
    if not cfg_path.exists():
        cfg_path = CONFIG_DIR / Path(args.config).name
    search = load_search_cfg(cfg_path)
    prefix = args.report_prefix or str(search.get("generation_id", "gen")).split("_")[0]
    root_seed = int(search["root_random_seed"])
    symbols = args.symbols or list(search["symbols_primary"])
    optuna_trials = int(args.optuna_trials or search.get("optuna_trials_per_proposal") or 4)
    n_llm = int(args.llm_proposals if args.llm_proposals is not None else search.get("llm_proposal_budget") or 4)

    registry = TrialRegistry()
    registry.log_event(
        "gen2_start",
        {
            "generation": search["generation_id"],
            "engine": "tradesim",
            "symbols": symbols,
            "root_seed": root_seed,
            "note": "preregistered sparse redesign; gates unchanged",
        },
    )

    # LLM proposals (Ollama)
    llm_specs: list[StrategySpec] = []
    if not args.no_llm:
        import os

        os.environ.setdefault("SMARTMONEY_LOAD_LLM", "1")
        os.environ.setdefault("SMARTMONEY_RAG_LIGHT", "1")
        print("Loading Ollama proposer...")
        proposer = StrategyProposer()
        llm_specs = proposer.propose_many(n=n_llm)
        # Force Gen2 frozen execution TF
        fixed_tf = search["search_space"]["execution_timeframe"][0]
        forced = []
        for s in llm_specs:
            d = s.model_dump()
            d["execution_timeframe"] = fixed_tf
            # Clamp other enums into search space
            for k, choices in search["search_space"].items():
                if k in d and d[k] not in choices:
                    d[k] = choices[0]
            forced.append(StrategySpec(**{k: v for k, v in d.items() if k in StrategySpec.model_fields}))
        llm_specs = forced
        print(f"LLM proposals: {len(llm_specs)} from {[m.name for m in proposer.models]}")

    sample = load_ohlcv(research_db(), symbols[0], "5m")
    if sample.empty:
        raise SystemExit("Research DB missing 5m — rebuild datasets including 5m")
    outer = build_outer_folds(
        int(sample["ts_ms"].min()),
        int(sample["ts_ms"].max()),
        "5m",
        search,
    )
    print(f"Outer folds: {len(outer)}")
    for f in outer:
        print(
            f"  fold {f.fold_id}: test "
            f"{pd.to_datetime(f.test_start_ms, unit='ms', utc=True).date()} -> "
            f"{pd.to_datetime(f.test_end_ms, unit='ms', utc=True).date()}"
        )

    families = search["families"]
    if args.families:
        families = [f for f in families if f["id"] in args.families]

    global_best = {"score": -1e18, "spec": None, "family": None}
    family_results = []
    for fam in families:
        print(f"\n=== {fam['id']}: {fam['description']} ===")
        best = run_family(
            fam, search, symbols, registry, root_seed, outer, optuna_trials, llm_specs
        )
        family_results.append(best)
        print(f" Best inner score={best['score']:.6f} family={best['family']}")
        if best["spec"] is not None and best["score"] > global_best["score"]:
            global_best = best

    if global_best["spec"] is None:
        # Fall back to H1 logical seed
        global_best["spec"] = StrategySpec.from_logical_seed(families[0]["logical_seed"]).to_params_dict()
        global_best["score"] = -1e18
        global_best["family"] = families[0]["id"]

    freeze_hash = registry.freeze_candidate(
        global_best["spec"],
        selection_basis=(
            f"gen2 inner_mean_expectancy={global_best['score']:.6f} "
            f"family={global_best['family']}; tradesim; never used outer OOS"
        ),
        code_version="0.2.0-gen2-tradesim",
    )
    search_out = {
        "generation": search["generation_id"],
        "freeze_hash": freeze_hash,
        "best_inner_score": global_best["score"],
        "best_family": global_best["family"],
        "spec": global_best["spec"],
        "family_results": [
            {"family": r["family"], "score": r["score"], "has_spec": r["spec"] is not None}
            for r in family_results
        ],
        "n_trials": registry.count_trials(),
        "engine": "tradesim",
    }
    (REPORTS / f"{prefix}_search_summary.json").write_text(
        json.dumps(search_out, indent=2, default=str), encoding="utf-8"
    )
    print("\n=== FREEZE ===")
    print(json.dumps(search_out, indent=2, default=str))

    print("\n=== OUTER OOS (once) ===")
    oos = evaluate_outer_oos(global_best["spec"], search, symbols, registry, root_seed)
    oos["freeze_hash"] = freeze_hash
    oos["spec"] = global_best["spec"]
    oos["best_family"] = global_best["family"]
    (REPORTS / f"{prefix}_oos_summary.json").write_text(
        json.dumps(oos, indent=2, default=str), encoding="utf-8"
    )
    registry.log_event(f"{prefix}_oos_complete", oos)
    registry.close()

    sitrep = {
        "maximum_earned_readiness": oos["readiness"],
        "evidence_class": oos["evidence_class"],
        "principal_blocker": oos["principal_blocker"],
        "generation": search["generation_id"],
        "engine": "tradesim (botsgeneral)",
        "authorization": "LIVE_STOP_RESEARCH_ONLY",
        "search": search_out,
        "oos": {k: v for k, v in oos.items() if k != "stitched_metrics"},
        "next_bounded_action": (
            "If failed: abandon or preregister a NEW generation with a new hypothesis BEFORE OOS — "
            "do not expand this generation's space after this OOS view."
        ),
    }
    (REPORTS / f"{prefix}_sitrep.json").write_text(json.dumps(sitrep, indent=2, default=str), encoding="utf-8")
    (REPORTS / f"{prefix}_sitrep.md").write_text(
        "\n".join(
            [
                f"# Sitrep — {search['generation_id']}",
                "",
                f"**Readiness:** `{oos['readiness']}`",
                f"**Blocker:** `{oos['principal_blocker']}`",
                f"**Engine:** tradesim (Bybit cost model, Binance RESEARCH_PROXY data)",
                f"**Family:** `{global_best['family']}`",
                f"**Pooled OOS trades:** {oos['pooled_trades']}",
                f"**Net PnL:** {oos['net_pnl']:.4f}",
                f"**PF:** {oos['pooled_pf']}",
                f"**Sharpe ann:** {oos['sharpe_daily_ann']:.4f}",
                f"**Freeze:** `{freeze_hash}`",
                "",
                "Authorization remains LIVE_STOP / RESEARCH_ONLY.",
                "",
            ]
        ),
        encoding="utf-8",
    )
    print((REPORTS / f"{prefix}_sitrep.md").read_text(encoding="utf-8"))


if __name__ == "__main__":
    main()
