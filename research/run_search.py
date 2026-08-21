"""Inner search: logical seed + LLM proposals + Optuna over primitive params.

Never selects using outer OOS. All trials append-only registered.
"""
from __future__ import annotations

import argparse
import json
from dataclasses import asdict
from pathlib import Path
from typing import Any, Optional

import numpy as np
import optuna
import yaml

from engine.backtest import BacktestConfig, run_backtest
from engine.data_loader import load_funding, load_ohlcv, research_db
from engine.features import compute_mtf_features
from engine.metrics import compute_metrics
from engine.walkforward import build_inner_folds, build_outer_folds, fold_seed
from llm.proposer import StrategyProposer
from llm.schema import StrategySpec
from paths import CONFIG_DIR, DATASETS, ensure_artifact_dirs
from research.registry import TrialRegistry
from smc.confluence import ConfluenceConfig


def load_yaml(name: str) -> dict:
    with open(CONFIG_DIR / name, encoding="utf-8") as f:
        return yaml.safe_load(f)


def slice_features(feat, start_ms: int, end_ms: int):
    return feat[(feat["ts_ms"] >= start_ms) & (feat["ts_ms"] < end_ms)].reset_index(drop=True)


def evaluate_spec_on_range(
    feat,
    spec: StrategySpec,
    symbol: str,
    start_ms: int,
    end_ms: int,
    profile: dict,
    funding_enabled: bool,
    seed: int,
) -> dict:
    sub = slice_features(feat, start_ms, end_ms)
    if len(sub) < 50:
        return {"n_trades": 0, "expectancy": -1e9, "net_pnl": 0.0, "profit_factor": 0.0, "status": "insufficient_bars"}

    # Recompute signals with this spec's confluence gates on precomputed base columns
    # For speed we reuse feature columns but re-score gates:
    from smc.confluence import score_confluence

    cfg = spec.to_confluence_config()
    scored = score_confluence(sub, cfg)
    for col in scored.columns:
        sub[col] = scored[col].to_numpy()

    # HTF gate if present
    if "htf_order_flow" in sub.columns:
        sub["long_signal"] = sub["long_signal"] & (sub["htf_order_flow"].fillna(0) >= 0)
        sub["short_signal"] = sub["short_signal"] & (sub["htf_order_flow"].fillna(0) <= 0)

    bt_cfg = BacktestConfig(
        initial_equity=float(profile.get("wallet_allocation_usdt", 10000)),
        risk_fraction=float(spec.risk_fraction),
        leverage=float(profile.get("default_leverage", 3)),
        taker_fee=float(profile.get("taker_fee", 0.0005)),
        maker_fee=float(profile.get("maker_fee", 0.0002)),
        slippage_bps=float(profile.get("baseline_slippage_bps", 1.0)),
        all_taker=True,
        target_rr=float(spec.target_rr),
        use_pd_targets=bool(spec.use_pd_targets),
        stop_beyond_sweep_atr_mult=float(spec.stop_beyond_sweep_atr_mult),
        max_hold_bars=int(spec.max_hold_bars),
        funding_enabled=funding_enabled,
    )
    funding = load_funding(DATASETS / "funding.sqlite", symbol) if funding_enabled else None
    result = run_backtest(sub, bt_cfg, symbol=symbol, funding=funding)
    metrics, extras = compute_metrics(result, n_trials_for_dsr=1, bootstrap_resamples=200, seed=seed)
    return {
        **asdict(metrics),
        **extras,
        "skipped_orders": result.skipped_orders,
        "status": "ok",
    }


def precompute_base_features(symbol: str, seed_spec: StrategySpec, profile: dict):
    db = research_db()
    cfg = seed_spec.to_confluence_config()
    return compute_mtf_features(
        db,
        symbol,
        cfg,
        bias_tf=seed_spec.bias_timeframe,
        structure_tf=seed_spec.structure_timeframe,
        execution_tf=seed_spec.execution_timeframe,
    )


def sample_spec_from_space(trial: optuna.Trial, base: StrategySpec, space: dict) -> StrategySpec:
    d = base.model_dump()
    for key, choices in space.items():
        if key not in d:
            continue
        if isinstance(choices[0], bool):
            d[key] = trial.suggest_categorical(key, choices)
        elif isinstance(choices[0], int):
            d[key] = trial.suggest_categorical(key, choices)
        elif isinstance(choices[0], float):
            d[key] = trial.suggest_categorical(key, choices)
        else:
            d[key] = trial.suggest_categorical(key, choices)
    d["name"] = f"optuna_{trial.number}"
    return StrategySpec(**d)


def run_search(
    max_proposals: Optional[int] = None,
    optuna_trials: Optional[int] = None,
    symbols: Optional[list[str]] = None,
    use_llm: bool = True,
) -> dict:
    ensure_artifact_dirs()
    profile = load_yaml("project_profile.yaml")
    search = load_yaml("search_space.yaml")
    root_seed = int(search["root_random_seed"])
    symbols = symbols or list(search.get("symbols_primary") or profile["primary_research_symbols"])
    max_proposals = int(max_proposals or search.get("llm_proposal_budget") or 5)
    optuna_trials = int(optuna_trials or search.get("optuna_trials_per_proposal") or 5)

    registry = TrialRegistry()
    registry.log_event("search_start", {"root_seed": root_seed, "symbols": symbols})

    # Funding availability
    from data.download_funding import funding_available

    funding_ok = funding_available()
    if not funding_ok:
        registry.log_event(
            "funding_status",
            {"available": False, "label": "funding_UNKNOWN_or_zero", "note": "Gate A honesty"},
        )

    # Proposals
    if use_llm:
        proposer = StrategyProposer()
        proposals = proposer.propose_many(n=max_proposals)
    else:
        proposals = [StrategySpec.from_logical_seed(search["logical_seed"])]

    # Determine data span from research db
    db = research_db()
    sample = load_ohlcv(db, symbols[0], proposals[0].execution_timeframe)
    if sample.empty:
        raise RuntimeError(
            "Research dataset empty. Run: python -m data.build_datasets"
        )
    data_start = int(sample["ts_ms"].min())
    data_end = int(sample["ts_ms"].max())
    outer = build_outer_folds(data_start, data_end, proposals[0].execution_timeframe, search)
    if not outer:
        raise RuntimeError("No outer folds constructed — check data span / fold config")

    # Selection uses ONLY the first outer fold's TRAIN span with nested inner folds
    # (never the outer test). Remaining outer tests reserved for run_oos.py.
    sel_fold = outer[0]
    inner_folds = build_inner_folds(
        sel_fold.train_start_ms,
        sel_fold.train_end_ms,
        proposals[0].execution_timeframe,
        search,
    )

    space = search["search_space"]
    best: dict[str, Any] = {"score": -1e18, "spec": None, "metrics": None}

    for p_i, prop in enumerate(proposals):
        # Precompute features for this timeframe stack (once per proposal family)
        print(f"Proposal {p_i}: {prop.name} ({prop.execution_timeframe})")
        try:
            feat_cache = {
                sym: precompute_base_features(sym, prop, profile) for sym in symbols
            }
        except Exception as exc:
            registry.log_trial(
                root_seed=root_seed,
                stage="proposal_feature_fail",
                params=prop.to_params_dict(),
                status="failed",
                proposal_source=prop.name,
                notes=str(exc),
            )
            continue

        def objective(trial: optuna.Trial) -> float:
            spec = sample_spec_from_space(trial, prop, space)
            # Keep proposal timeframes unless space overrides
            fold_scores = []
            for inf in inner_folds:
                seed = fold_seed(root_seed, inf.fold_id, trial.number)
                sym_scores = []
                for sym in symbols:
                    feat = feat_cache[sym]
                    if feat.empty:
                        continue
                    m = evaluate_spec_on_range(
                        feat,
                        spec,
                        sym,
                        inf.test_start_ms,
                        inf.test_end_ms,
                        profile,
                        funding_enabled=funding_ok,
                        seed=seed,
                    )
                    registry.log_trial(
                        root_seed=root_seed,
                        stage="inner",
                        params=spec.to_params_dict(),
                        status=m.get("status", "ok"),
                        fold_id=inf.fold_id,
                        symbol=sym,
                        proposal_source=prop.name,
                        metrics=m,
                    )
                    sym_scores.append(m.get("expectancy", -1e9))
                if sym_scores:
                    fold_scores.append(float(np.mean(sym_scores)))
            score = float(np.mean(fold_scores)) if fold_scores else -1e9
            trial.set_user_attr("spec", spec.to_params_dict())
            return score

        sampler = optuna.samplers.TPESampler(seed=fold_seed(root_seed, p_i, 0))
        study = optuna.create_study(direction="maximize", sampler=sampler)
        # Always evaluate the logical/proposal defaults first
        study.enqueue_trial({k: prop.to_params_dict()[k] for k in space.keys() if k in prop.to_params_dict()})
        study.optimize(objective, n_trials=optuna_trials, show_progress_bar=False)

        if study.best_trial is not None:
            spec_dict = study.best_trial.user_attrs.get("spec") or sample_spec_from_space(
                study.best_trial, prop, space
            ).to_params_dict()
            score = float(study.best_value)
            registry.log_trial(
                root_seed=root_seed,
                stage="inner_best",
                params=spec_dict,
                status="selected_candidate",
                proposal_source=prop.name,
                metrics={"inner_mean_expectancy": score},
            )
            if score > best["score"]:
                best = {"score": score, "spec": spec_dict, "metrics": {"inner_mean_expectancy": score}}

    if best["spec"] is None:
        best["spec"] = StrategySpec.from_logical_seed(search["logical_seed"]).to_params_dict()
        best["score"] = -1e18
        best["metrics"] = {"note": "no_positive_inner_result_froze_logical_seed"}

    h = registry.freeze_candidate(
        best["spec"],
        selection_basis=f"inner_mean_expectancy={best['score']:.6f}; never used outer OOS",
    )
    out = {
        "freeze_hash": h,
        "best_inner_score": best["score"],
        "spec": best["spec"],
        "n_trials_logged": registry.count_trials(),
        "funding_available": funding_ok,
        "outer_folds_reserved": len(outer),
    }
    registry.log_event("search_complete", out)
    registry.close()
    path = DATASETS.parent / "reports"
    path.mkdir(parents=True, exist_ok=True)
    (path / "search_summary.json").write_text(json.dumps(out, indent=2, default=str), encoding="utf-8")
    print(json.dumps(out, indent=2, default=str))
    return out


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--max-proposals", type=int, default=None)
    p.add_argument("--optuna-trials", type=int, default=None)
    p.add_argument("--symbols", nargs="+", default=None)
    p.add_argument("--no-llm", action="store_true")
    args = p.parse_args()
    run_search(args.max_proposals, args.optuna_trials, args.symbols, use_llm=not args.no_llm)


if __name__ == "__main__":
    main()
