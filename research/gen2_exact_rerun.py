"""Re-run Gen2 EXACTLY like evaluate_outer_oos (full-history features) — invalidation check."""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

from engine.data_loader import load_funding, research_db
from engine.features import compute_mtf_features
from engine.tradesim_adapter import run_tradesim_on_features
from llm.schema import StrategySpec
from paths import DATASETS, REPORTS
from smc.confluence import score_confluence


def funding_arrays(symbol: str):
    df = load_funding(DATASETS / "funding.sqlite", symbol)
    if df.empty:
        return None, None
    return df["funding_time_ms"].to_numpy(np.int64), df["funding_rate"].to_numpy(float)


def slice_feat(feat: pd.DataFrame, start_ms: int, end_ms: int) -> pd.DataFrame:
    return feat[(feat["ts_ms"] >= start_ms) & (feat["ts_ms"] < end_ms)].copy()


def evaluate_window(feat, spec, symbol, start_ms, end_ms):
    sub = slice_feat(feat, start_ms, end_ms)
    if len(sub) < 50:
        return {"n_trades": 0, "net_pnl": 0.0, "profit_factor": float("nan"), "gross_profit": 0.0, "gross_loss": 0.0}
    cfg = spec.to_confluence_config()
    scored = score_confluence(sub, cfg)
    for col in scored.columns:
        sub[col] = scored[col].to_numpy()
    if "htf_order_flow" in sub.columns:
        sub["long_signal"] = sub["long_signal"] & (sub["htf_order_flow"].fillna(0) >= 0)
        sub["short_signal"] = sub["short_signal"] & (sub["htf_order_flow"].fillna(0) <= 0)
    fts, fr = funding_arrays(symbol)
    return run_tradesim_on_features(
        sub,
        symbol,
        spec.execution_timeframe,
        target_rr=float(spec.target_rr),
        stop_beyond_sweep_atr_mult=float(spec.stop_beyond_sweep_atr_mult),
        use_pd_targets=bool(spec.use_pd_targets),
        max_hold_bars=int(spec.max_hold_bars),
        funding_ts_ms=fts,
        funding_rate=fr,
        strategy_id=f"gen2_recon_{symbol}",
        print_headline=False,
    )


def main() -> None:
    oos = json.loads(Path("artifacts/reports/gen2_oos_summary.json").read_text(encoding="utf-8"))
    # Gen2 freeze predates session_mode; default none
    raw = dict(oos["spec"])
    raw.setdefault("session_mode", "none")
    raw.setdefault("confirm_bars", 0)
    spec = StrategySpec(**{k: v for k, v in raw.items() if k in StrategySpec.model_fields})
    symbols = ["BTCUSDT", "ETHUSDT"]
    print("Precomputing full-history features (Gen2 freeze)...")
    print(f"spec={spec.name} OB={spec.require_order_block} session={spec.session_mode}")
    cache = {
        sym: compute_mtf_features(
            research_db(),
            sym,
            spec.to_confluence_config(),
            bias_tf=spec.bias_timeframe,
            structure_tf=spec.structure_timeframe,
            execution_tf=spec.execution_timeframe,
        )
        for sym in symbols
    }

    folds = oos["fold_summaries"]
    out = {
        "generation": oos.get("generation"),
        "freeze_hash": oos.get("freeze_hash"),
        "reported_net": oos["net_pnl"],
        "reported_pf": oos["pooled_pf"],
        "reported_sharpe": oos.get("sharpe_daily_ann"),
        "folds": [],
        "stitched": [],
    }

    for f in folds:
        net = 0.0
        n = 0
        gp = gl = 0.0
        per = {}
        for sym in symbols:
            m = evaluate_window(cache[sym], spec, sym, f["test_start_ms"], f["test_end_ms"])
            per[sym] = {"n": m.get("n_trades"), "net": m.get("net_pnl"), "pf": m.get("profit_factor")}
            net += float(m.get("net_pnl", 0))
            n += int(m.get("n_trades", 0))
            gp += float(m.get("gross_profit", 0) or 0)
            gl += float(m.get("gross_loss", 0) or 0)
        row = {
            "fold_id": f["fold_id"],
            "reported_net": f["net_pnl"],
            "rerun_net": net,
            "rerun_n": n,
            "rerun_pf": (gp / gl) if gl > 0 else None,
            "per_symbol": per,
            "start": str(pd.to_datetime(f["test_start_ms"], unit="ms", utc=True)),
            "end": str(pd.to_datetime(f["test_end_ms"], unit="ms", utc=True)),
        }
        out["folds"].append(row)
        print(
            f"fold {f['fold_id']}: reported_net={f['net_pnl']:.2f} rerun_net={net:.2f} "
            f"n={n} delta={net - f['net_pnl']:.2f}"
        )

    gp = gl = 0.0
    net = 0.0
    n = 0
    sharpes = []
    for sym in symbols:
        parts = [slice_feat(cache[sym], f["test_start_ms"], f["test_end_ms"]) for f in folds]
        stitched = pd.concat(parts, ignore_index=True)
        scored = score_confluence(stitched, spec.to_confluence_config())
        for col in scored.columns:
            stitched[col] = scored[col].to_numpy()
        if "htf_order_flow" in stitched.columns:
            stitched["long_signal"] = stitched["long_signal"] & (stitched["htf_order_flow"].fillna(0) >= 0)
            stitched["short_signal"] = stitched["short_signal"] & (stitched["htf_order_flow"].fillna(0) <= 0)
        fts, fr = funding_arrays(sym)
        m = run_tradesim_on_features(
            stitched,
            sym,
            spec.execution_timeframe,
            target_rr=float(spec.target_rr),
            stop_beyond_sweep_atr_mult=float(spec.stop_beyond_sweep_atr_mult),
            use_pd_targets=bool(spec.use_pd_targets),
            max_hold_bars=int(spec.max_hold_bars),
            funding_ts_ms=fts,
            funding_rate=fr,
            strategy_id=f"gen2_recon_stitch_{sym}",
            print_headline=True,
        )
        out["stitched"].append(
            {
                "symbol": sym,
                "n": m.get("n_trades"),
                "net": m.get("net_pnl"),
                "pf": m.get("profit_factor"),
                "sharpe": m.get("sharpe_ann"),
                "gross_profit": m.get("gross_profit"),
                "gross_loss": m.get("gross_loss"),
            }
        )
        n += int(m.get("n_trades", 0))
        net += float(m.get("net_pnl", 0))
        gp += float(m.get("gross_profit", 0) or 0)
        gl += float(m.get("gross_loss", 0) or 0)
        sharpes.append(float(m.get("sharpe_ann", 0) or 0))

    # last 4m
    a = int(pd.Timestamp("2025-12-19", tz="UTC").timestamp() * 1000)
    b = int(pd.Timestamp("2026-04-19", tz="UTC").timestamp() * 1000)
    net4 = n4 = 0
    gp4 = gl4 = 0.0
    for sym in symbols:
        m = evaluate_window(cache[sym], spec, sym, a, b)
        net4 += float(m.get("net_pnl", 0))
        n4 += int(m.get("n_trades", 0))
        gp4 += float(m.get("gross_profit", 0) or 0)
        gl4 += float(m.get("gross_loss", 0) or 0)
        print(f"last4m {sym}: n={m.get('n_trades')} net={float(m.get('net_pnl',0)):.2f} pf={m.get('profit_factor')}")

    pooled_pf = (gp / gl) if gl > 0 else None
    out["last_4m"] = {"n": n4, "net": net4, "pf": (gp4 / gl4) if gl4 > 0 else None}
    out["stitched_pooled"] = {
        "n": n,
        "net": net,
        "pf": pooled_pf,
        "mean_symbol_sharpe": float(np.mean(sharpes)) if sharpes else None,
    }
    # Invalidation: material mismatch vs reported positive claim
    out["verdict"] = {
        "reproduces_positive_edge": bool(net > 0 and pooled_pf is not None and pooled_pf >= 1.20),
        "matches_reported_sign": bool((oos["net_pnl"] > 0) == (net > 0)),
        "invalidated": bool(net <= 0 or (pooled_pf is not None and pooled_pf < 1.0)),
        "note": "Same freeze + full-history path as Gen4 invalidation check",
    }
    path = REPORTS / "gen2_exact_rerun.json"
    path.write_text(json.dumps(out, indent=2, default=str), encoding="utf-8")
    print(json.dumps(out["stitched_pooled"], indent=2))
    print("last4m pooled", out["last_4m"])
    print("VERDICT", json.dumps(out["verdict"], indent=2))
    print(f"wrote {path}")


if __name__ == "__main__":
    main()
