"""Gate B remainder + Gate C/D for frozen tsm_chandelier 1h nested OOS.

Does not retune. Replays stitched outer OOS once for baseline trade PnLs,
Deflated Sharpe Ratio (DSR), dependence-aware block bootstrap, and full
2× / 3× slippage-stress re-sims via CostConfig.slippage_stress_multiplier.

Runs tradesim conformance in-process so SimResult stamps are GREEN, passes
Last-as-Mark proxy bars for RESEARCH_PROXY modelling, and refuses to claim
SHADOW_READY unless assert_quotable succeeds.
"""

from __future__ import annotations

import json
import subprocess
import sys
from dataclasses import replace
from pathlib import Path

import numpy as np
import pandas as pd
import yaml

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tradesim.ensure_source import prefer_botsgeneral_tradesim

prefer_botsgeneral_tradesim()

from engine.data_loader import load_ohlcv, research_db
from engine.metrics import block_bootstrap_positive_expectancy, deflated_sharpe_ratio
from engine.tradesim_adapter import PROJECT_STARTING_EQUITY_USDT, df_to_barseries
from engine.walkforward import build_outer_folds, ms_per_bar
from paths import CONFIG_DIR, REPORTS, ensure_artifact_dirs
from strategies.tsm_chandelier.signals import build_signal_frame, to_tradesim_signals
from tradesim import (
    assert_quotable,
    compute_metrics,
    research_costs,
    research_instrument,
    research_margin,
    research_sim,
    research_sizing,
    simulate,
)
from tradesim.conformance.stamp import ConformanceStamp, last_stamp, record_stamp

try:
    from research.run_gen2 import funding_arrays
except Exception:  # noqa: BLE001
    funding_arrays = None  # type: ignore

TRADESIM_ROOT = Path(__import__("tradesim").__file__).resolve().parents[2]
TRADESIM_TESTS = TRADESIM_ROOT / "tests"


def _count_tsm_exploratory_trials() -> int:
    """Upper-bound sensitivity: every baseline/OOS metric row under artifacts/reports/tsm_*."""
    n = 0
    base = REPORTS
    if not base.exists():
        return 1
    for p in base.glob("tsm_*/baseline_h0.json"):
        try:
            rows = json.loads(p.read_text(encoding="utf-8"))
            if isinstance(rows, list):
                n += sum(1 for r in rows if r.get("status") in ("ok", "no_signals", "no_data"))
        except Exception:  # noqa: BLE001
            continue
    for p in base.glob("tsm_*/*_oos_summary.json"):
        n += 1
    return max(n, 1)


def _stamp_from_dict(d: dict) -> ConformanceStamp:
    return ConformanceStamp(
        engine_name=str(d["engine_name"]),
        engine_version=str(d["engine_version"]),
        engine_commit=str(d["engine_commit"]),
        fixture_pack_hash=str(d["fixture_pack_hash"]),
        registry_digest=str(d["registry_digest"]),
        contract=str(d["contract"]),
        checked_at_ms=int(d["checked_at_ms"]),
        passed=bool(d["passed"]),
        required_count=int(d["required_count"]),
        satisfied_count=int(d["satisfied_count"]),
        unsatisfied=tuple(d.get("unsatisfied") or ()),
        checker_version=str(d.get("checker_version") or "1"),
        detail=dict(d.get("detail") or {}),
    )


def _run_conformance() -> dict:
    """Run tradesim-conformance in a subprocess, then record the stamp here.

    Nested in-process pytest (VALD meta-tests) is flaky on Windows when the
    checker itself is invoked from another Python entrypoint; the CLI path is
    the supported grading surface.
    """
    out_path = REPORTS / "tsm_chandelier" / "tradesim_conformance_report.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        sys.executable,
        "-m",
        "tradesim.conformance.checker",
        "--engine",
        "tradesim",
        "--contract",
        "perp_bracket_backtest",
        "--tests",
        str(TRADESIM_TESTS),
        "--json",
        str(out_path),
        "--quiet",
    ]
    proc = subprocess.run(
        cmd,
        cwd=str(TRADESIM_ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    if proc.returncode != 0:
        print(proc.stdout[-4000:] if proc.stdout else "")
        print(proc.stderr[-4000:] if proc.stderr else "")
        raise SystemExit(f"tradesim-conformance exited {proc.returncode}")
    report = json.loads(out_path.read_text(encoding="utf-8"))
    stamp = _stamp_from_dict(report["stamp"])
    record_stamp(stamp)
    out = {
        "ok": bool(report.get("ok")),
        "required": int(report.get("required", 0)),
        "satisfied": int(report.get("satisfied", 0)),
        "unsatisfied": list(report.get("unsatisfied") or []),
        "stamp": stamp.as_dict(),
        "is_green": bool(stamp.is_green),
        "one_line": stamp.one_line(),
        "tests_path": str(TRADESIM_TESTS),
        "method": "subprocess_cli_then_record_stamp",
    }
    print("CONFORMANCE", stamp.one_line())
    return out


def _stitch_and_sim(*, costs, label: str, print_headline: bool = False):
    cfg = yaml.safe_load((CONFIG_DIR / "search_space_tsm_chandelier_1h.yaml").read_text(encoding="utf-8"))
    symbols = list(cfg["symbols_primary"])
    timeframe = str(cfg["execution_timeframe"])
    warmup = int(cfg.get("warmup_bars", 80))
    max_hold = int(cfg.get("max_hold_bars", 36))
    db = research_db()
    sample = load_ohlcv(db, symbols[0], timeframe)
    outer = build_outer_folds(
        int(sample["ts_ms"].min()),
        int(sample["ts_ms"].max()),
        timeframe,
        cfg,
    )
    bar_ms = ms_per_bar(timeframe)
    per_sym = []
    all_pnls = []
    liq_statuses = []
    stamp_green_flags = []
    for sym in symbols:
        bars_df = load_ohlcv(db, sym, timeframe)
        touch = load_ohlcv(db, sym, "1m")
        parts = []
        for fold in outer:
            feat_start = fold.test_start_ms - warmup * bar_ms
            window = bars_df[(bars_df["ts_ms"] >= feat_start) & (bars_df["ts_ms"] < fold.test_end_ms)].copy()
            if window.empty:
                continue
            feat = build_signal_frame(window.reset_index(drop=True))
            mask = feat["ts_ms"].to_numpy(np.int64) < fold.test_start_ms
            feat.loc[mask, "long_signal"] = False
            feat.loc[mask, "short_signal"] = False
            parts.append(feat[feat["ts_ms"] >= fold.test_start_ms].copy())
        if not parts:
            continue
        stitched = (
            pd.concat(parts, ignore_index=True)
            .drop_duplicates(subset=["ts_ms"])
            .sort_values("ts_ms")
            .reset_index(drop=True)
        )
        signals = to_tradesim_signals(stitched, sym, max_hold)
        t0 = int(stitched["ts_ms"].min())
        t1 = int(stitched["ts_ms"].max()) + bar_ms
        touch_slice = touch[(touch["ts_ms"] >= t0) & (touch["ts_ms"] < t1)] if not touch.empty else touch
        fts = fr = None
        if funding_arrays is not None:
            try:
                fts, fr = funding_arrays(sym)
            except Exception:  # noqa: BLE001
                fts = fr = None
        bars = df_to_barseries(stitched, timeframe, sym)
        # RESEARCH_PROXY Mark = Last (execution OHLC). Native Bybit Mark is required for parity PASS.
        mark_bars = bars
        touch_bs = df_to_barseries(touch_slice, "1m", sym) if not touch_slice.empty else None
        result = simulate(
            bars=bars,
            signals=signals,
            instrument=research_instrument(sym),
            costs=costs,
            margin=research_margin(leverage=1.0),
            sizing=research_sizing(),
            sim=research_sim(starting_equity=PROJECT_STARTING_EQUITY_USDT),
            touch_bars=touch_bs,
            mark_bars=mark_bars,
            funding_ts_ms=fts,
            funding_rate=fr,
            run_id=f"tsm_chandelier_{sym.lower()}_1h_{label}",
            attach_stamp=True,
        )
        assert_quotable(result.stamp, result=result)
        m = compute_metrics(result, annualisation_days=365.0, bars=bars)
        if print_headline:
            from tradesim import headline_table

            print(headline_table(m))
        pnls = np.asarray([float(t.realized_pnl) for t in result.trades], dtype=float)
        gp = float(pnls[pnls > 0].sum()) if pnls.size else 0.0
        gl = float((-pnls[pnls < 0]).sum()) if pnls.size else 0.0
        liq_status = str(getattr(result, "liquidation_status", "UNKNOWN"))
        liq_statuses.append(liq_status)
        stamp_obj = result.stamp
        if isinstance(stamp_obj, dict):
            stamp_green = bool(stamp_obj.get("passed")) and int(stamp_obj.get("satisfied_count", 0)) >= int(
                stamp_obj.get("required_count", 1)
            )
            stamp_dict = stamp_obj
        elif stamp_obj is not None:
            stamp_green = bool(stamp_obj.is_green)
            stamp_dict = stamp_obj.as_dict()
        else:
            stamp_green = False
            stamp_dict = None
        stamp_green_flags.append(stamp_green)
        per_sym.append(
            {
                "symbol": sym,
                "n_trades": int(m.n_trades),
                "net_pnl": float(m.net_pnl),
                "profit_factor": float(m.profit_factor),
                "expectancy": float(m.expectancy),
                "win_rate": float(m.win_rate),
                "sharpe_ann": float(m.sharpe.annualised) if m.sharpe else 0.0,
                "hac_sharpe_ann": float(m.sharpe.hac_annualised) if m.sharpe else 0.0,
                "max_drawdown": float(m.max_drawdown_pct),
                "gross_profit": gp,
                "gross_loss": gl,
                "total_fees": float(m.total_fees),
                "total_slippage": float(m.total_slippage),
                "liquidations": int(getattr(m, "n_liquidations", 0) or 0),
                "liquidation_status": liq_status,
                "stamp_green": stamp_green,
                "stamp": stamp_dict,
            }
        )
        all_pnls.append(pnls)
        print(
            f"[{label}] {sym}: n={m.n_trades} PF={m.profit_factor:.4f} "
            f"pnl={m.net_pnl:.2f} sharpe={per_sym[-1]['sharpe_ann']:.3f} "
            f"liq={liq_status} stamp_green={stamp_green}"
        )
    pnls = np.concatenate(all_pnls) if all_pnls else np.array([], dtype=float)
    gp = float(sum(x["gross_profit"] for x in per_sym))
    gl = float(sum(x["gross_loss"] for x in per_sym))
    pooled_pf = (gp / gl) if gl > 0 else (float("inf") if gp > 0 else float("nan"))
    # worst liquidation status across symbols
    rank = {"MODELLED": 0, "SIMPLIFIED": 1, "UNKNOWN": 2}
    worst_liq = "UNKNOWN"
    if liq_statuses:
        worst_liq = max(liq_statuses, key=lambda s: rank.get(s, 3))
    return {
        "per_symbol": per_sym,
        "pnls": pnls,
        "pooled_trades": int(len(pnls)),
        "net_pnl": float(sum(x["net_pnl"] for x in per_sym)),
        "pooled_pf": float(pooled_pf),
        "expectancy": float(pnls.mean()) if pnls.size else 0.0,
        "sharpe_ann_mean": float(np.nanmean([x["sharpe_ann"] for x in per_sym])) if per_sym else 0.0,
        "hac_sharpe_ann_mean": float(np.nanmean([x["hac_sharpe_ann"] for x in per_sym])) if per_sym else 0.0,
        "max_drawdown": float(max((x["max_drawdown"] for x in per_sym), default=0.0)),
        "liquidations": int(sum(x["liquidations"] for x in per_sym)),
        "liquidation_status": worst_liq,
        "all_stamps_green": bool(stamp_green_flags) and all(stamp_green_flags),
        "n_outer_folds": len(outer),
        "oos_start_ms": int(outer[0].test_start_ms) if outer else 0,
        "oos_end_ms": int(outer[-1].test_end_ms) if outer else 0,
        "mark_proxy": "execution_ohlc_last_as_mark_RESEARCH_PROXY",
    }


def _gate_d(pnls: np.ndarray, fold_summaries: list[dict]) -> dict:
    if pnls.size == 0:
        return {"pass": False, "reason": "no_trades"}
    i_best = int(np.argmax(pnls))
    excl_best = float(pnls.sum() - pnls[i_best])
    fold_pnls = [float(f["net_pnl"]) for f in fold_summaries]
    best_fold = max(fold_pnls) if fold_pnls else 0.0
    pos_total = sum(x for x in fold_pnls if x > 0)
    best_fold_share = (best_fold / pos_total) if pos_total > 0 else float("nan")
    excl_best_fold = float(sum(fold_pnls) - best_fold)
    checks = {
        "pnl_excluding_best_trade_positive": excl_best > 0,
        "pnl_excluding_best_fold_positive": excl_best_fold > 0,
        "best_fold_share_of_positive_pnl_le_40pct": bool(best_fold_share == best_fold_share and best_fold_share <= 0.40),
    }
    return {
        "checks": checks,
        "pass": all(checks.values()),
        "excl_best_trade_pnl": excl_best,
        "excl_best_fold_pnl": excl_best_fold,
        "best_fold_share_of_positive_pnl": best_fold_share,
        "note": "Year exclusion approximated by outer-fold exclusion (no calendar-year trade timestamps in this script).",
    }


def main() -> None:
    ensure_artifact_dirs()
    oos_path = REPORTS / "tsm_chandelier" / "1h_oos_summary.json"
    oos = json.loads(oos_path.read_text(encoding="utf-8"))
    gates = yaml.safe_load((CONFIG_DIR / "frozen_gates.yaml").read_text(encoding="utf-8"))
    hist = gates.get("historical_edge", gates.get("gate_b", {}))
    dsr_min = float(hist.get("dsr_min", 0.95))
    boot_min = float(hist.get("bootstrap_positive_expectancy_min", hist.get("bootstrap_pos_exp_min", 0.90)))
    stress_pf_min = float(gates.get("cost_stress", {}).get("moderate_pooled_pf_min", 1.05))

    print("=== tradesim conformance (in-process) ===")
    conf = _run_conformance()
    if not conf["is_green"]:
        raise SystemExit(f"conformance not green: {conf['one_line']}")
    if last_stamp() is None or not last_stamp().is_green:
        raise SystemExit("last_stamp missing/not green after checker")

    base_costs = research_costs()
    print("=== baseline stitched OOS replay (quotable path) ===")
    baseline = _stitch_and_sim(costs=base_costs, label="baseline_gatebcd", print_headline=True)
    pnls = baseline["pnls"]

    n_obs = max(
        2,
        int(round((baseline["oos_end_ms"] - baseline["oos_start_ms"]) / 86_400_000)),
    )
    sharpe_ann = float(oos.get("sharpe_daily_ann_mean_symbols") or baseline["sharpe_ann_mean"])
    n_trials_prereg = 1  # search_space trial_budget_total
    n_trials_family = _count_tsm_exploratory_trials()
    dsr_prereg = deflated_sharpe_ratio(sharpe_ann, n_obs, n_trials_prereg)
    dsr_family = deflated_sharpe_ratio(sharpe_ann, n_obs, n_trials_family)

    print("=== block bootstrap (10_000) ===")
    boot = block_bootstrap_positive_expectancy(pnls, n_resamples=10_000, block=5, seed=20260810)

    print("=== moderate stress 2x slip ===")
    stress2 = _stitch_and_sim(
        costs=replace(base_costs, slippage_stress_multiplier=2.0),
        label="stress2x_slip",
        print_headline=False,
    )
    print("=== severe stress 3x slip (report only) ===")
    stress3 = _stitch_and_sim(
        costs=replace(base_costs, slippage_stress_multiplier=3.0),
        label="stress3x_slip",
        print_headline=False,
    )

    gate_d = _gate_d(pnls, oos.get("fold_summaries", []))

    checks = {
        "dsr_preregistered_n_trials_1": bool(dsr_prereg >= dsr_min),
        "bootstrap_pos_exp": bool(boot >= boot_min),
        "moderate_stress_net_pnl_positive": bool(stress2["net_pnl"] > 0),
        "moderate_stress_pooled_pf": bool(
            stress2["pooled_pf"] == stress2["pooled_pf"] and stress2["pooled_pf"] >= stress_pf_min
        ),
        "moderate_stress_no_liquidation": bool(stress2["liquidations"] == 0),
        "gate_d_concentration": bool(gate_d["pass"]),
        "engine_conformance_green": bool(conf["is_green"] and baseline["all_stamps_green"]),
        "liquidation_not_unknown": bool(baseline["liquidation_status"] != "UNKNOWN"),
        "assert_quotable_baseline": True,  # raised if failed during sim
        "pbo_matrix_available": False,
    }
    core_pass = (
        checks["dsr_preregistered_n_trials_1"]
        and checks["bootstrap_pos_exp"]
        and checks["moderate_stress_net_pnl_positive"]
        and checks["moderate_stress_pooled_pf"]
        and checks["moderate_stress_no_liquidation"]
        and checks["engine_conformance_green"]
        and checks["liquidation_not_unknown"]
    )

    if not checks["engine_conformance_green"]:
        readiness = "LIVE_STOP / RESEARCH_ONLY_ENGINE_NOT_GREEN"
        principal = "engine_conformance_not_green"
    elif not checks["liquidation_not_unknown"]:
        readiness = "LIVE_STOP / RESEARCH_ONLY_LIQUIDATION_UNKNOWN"
        principal = "liquidation_status_unknown"
    elif not core_pass:
        readiness = "LIVE_STOP / RESEARCH_ONLY_FAILED_GATES"
        principal = next(
            k
            for k, v in checks.items()
            if not v and k not in ("pbo_matrix_available",)
        )
    elif not checks["gate_d_concentration"]:
        readiness = "LIVE_STOP / RESEARCH_ONLY_FAILED_GATE_D"
        principal = "gate_d_concentration"
    else:
        readiness = "LIVE_STOP / SHADOW_READY"
        principal = None

    summary = {
        "maximum_earned_readiness": readiness,
        "evidence_class": "nested_outer_oos_stitched_tradesim_RESEARCH_PROXY",
        "generation_id": oos.get("generation_id"),
        "principal_blocker": principal,
        "conformance": conf,
        "baseline_replay": {k: v for k, v in baseline.items() if k != "pnls"},
        "dsr": {
            "observed_sharpe_ann": sharpe_ann,
            "n_obs_days": n_obs,
            "n_trials_preregistered": n_trials_prereg,
            "dsr_preregistered": dsr_prereg,
            "dsr_preregistered_pass": checks["dsr_preregistered_n_trials_1"],
            "n_trials_tsm_family_sensitivity": n_trials_family,
            "dsr_family_sensitivity": dsr_family,
            "dsr_family_pass": bool(dsr_family >= dsr_min),
            "note": (
                "Primary DSR uses preregistered trial_budget_total=1 for this fixed-H0 generation. "
                "Family sensitivity counts other TSM baseline/OOS rows as multiple-testing stress."
            ),
        },
        "bootstrap": {
            "n_resamples": 10_000,
            "block": 5,
            "seed": 20260810,
            "frac_positive_expectancy": boot,
            "pass": checks["bootstrap_pos_exp"],
            "threshold": boot_min,
        },
        "moderate_stress_2x_slip": {k: v for k, v in stress2.items() if k != "pnls"},
        "severe_stress_3x_slip_report_only": {k: v for k, v in stress3.items() if k != "pnls"},
        "gate_d": gate_d,
        "checks": checks,
        "pbo_status": "PBO_UNAVAILABLE_INSUFFICIENT_MATRIX",
        "live_authorization": "NOT_GRANTED — readiness ≠ authorization; user must approve any live/shadow deploy",
        "cannot_claim": [
            "SCALE_CANDIDATE",
            "MICRO_LIVE without forward shadow + ops tests",
            "Bybit native parity PASS (evidence remains RESEARCH_PROXY: Binance OHLCV + Last-as-Mark)",
        ],
        "notes": [
            "Historical max without forward shadow is SHADOW_READY.",
            "botsgeneral working tree may stamp UNKNOWN_DIRTY; grade can still be GREEN if identifiers pass.",
            "DSR family sensitivity may fail while preregistered DSR passes — primary claim uses trial_budget_total=1.",
        ],
    }

    out_dir = REPORTS / "tsm_chandelier"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "1h_gate_bcd_summary.json"
    out_path.write_text(json.dumps(summary, indent=2, default=str), encoding="utf-8")
    sitrep = out_dir / "1h_gate_bcd_sitrep.md"
    sitrep.write_text(
        "\n".join(
            [
                "# Sitrep — tsm_chandelier Gate B remainder + Gate C/D",
                "",
                f"- **Maximum earned readiness:** `{readiness}`",
                f"- **Principal blocker:** `{principal}`",
                f"- **Engine conformance:** {conf['one_line']}",
                f"- **Liquidation status (baseline):** {baseline['liquidation_status']}",
                f"- **DSR (n_trials=1 preregistered):** {dsr_prereg:.4f} (pass≥{dsr_min})",
                f"- **DSR family sensitivity (n_trials={n_trials_family}):** {dsr_family:.4f}",
                f"- **Bootstrap pos expectancy:** {boot:.4f} (pass≥{boot_min})",
                f"- **Moderate 2× slip:** PF={stress2['pooled_pf']:.4f} pnl={stress2['net_pnl']:.2f} liq={stress2['liquidations']}",
                f"- **Severe 3× slip (report):** PF={stress3['pooled_pf']:.4f} pnl={stress3['net_pnl']:.2f}",
                f"- **Gate D concentration:** {gate_d['pass']}",
                "",
                "## Checks",
                "",
                *[f"- `{k}`: `{v}`" for k, v in checks.items()],
                "",
                "Authorization remains LIVE_STOP until the user explicitly approves live/shadow.",
                "",
            ]
        ),
        encoding="utf-8",
    )
    oos["gate_bcd"] = {
        "summary_path": str(out_path),
        "maximum_earned_readiness": readiness,
        "principal_blocker": principal,
        "dsr_preregistered": dsr_prereg,
        "bootstrap_pos_exp": boot,
        "moderate_stress_pf": stress2["pooled_pf"],
        "liquidation_status": baseline["liquidation_status"],
        "engine_conformance_green": checks["engine_conformance_green"],
    }
    oos["maximum_earned_readiness"] = readiness
    oos["principal_blocker"] = principal
    oos_path.write_text(json.dumps(oos, indent=2, default=str), encoding="utf-8")
    print("Wrote", out_path)
    print("Wrote", sitrep)
    print("READINESS", readiness, "blocker", principal)
    print(
        json.dumps(
            {
                k: summary[k]
                for k in (
                    "dsr",
                    "bootstrap",
                    "checks",
                    "maximum_earned_readiness",
                    "principal_blocker",
                )
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
