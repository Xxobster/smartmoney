"""Freeze package + monthly trade distribution for tsm_chandelier (BTC/ETH/SOL)."""

from __future__ import annotations

import hashlib
import json
import sqlite3
import sys
from datetime import datetime, timezone
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
from engine.tradesim_adapter import PROJECT_STARTING_EQUITY_USDT, df_to_barseries
from engine.walkforward import build_outer_folds, ms_per_bar
from paths import CONFIG_DIR, REPORTS, ensure_artifact_dirs
from strategies.tsm_chandelier.signals import (
    STRATEGY_ID,
    STRATEGY_VERSION,
    build_signal_frame,
    to_tradesim_signals,
)
from tradesim import research_costs, research_instrument, research_margin, research_sim, research_sizing, simulate
from tradesim.conformance.stamp import ConformanceStamp, record_stamp

try:
    from research.run_gen2 import funding_arrays
except Exception:  # noqa: BLE001
    funding_arrays = None  # type: ignore

SYMBOLS = ["BTCUSDT", "ETHUSDT", "SOLUSDT"]
TIMEFRAME = "1h"
MAX_HOLD = 36
WARMUP = 80


def _file_sha256(path: Path) -> str:
    h = hashlib.sha256()
    h.update(path.read_bytes())
    return h.hexdigest()


def _canonical_json(obj) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), default=str)


def _load_green_stamp() -> ConformanceStamp | None:
    p = REPORTS / "tsm_chandelier" / "tradesim_conformance_report.json"
    if not p.exists():
        return None
    d = json.loads(p.read_text(encoding="utf-8"))["stamp"]
    st = ConformanceStamp(
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
    record_stamp(st)
    return st


def symbol_coverage(db: str) -> dict:
    con = sqlite3.connect(db)
    try:
        tables = [r[0] for r in con.execute("select name from sqlite_master where type='table'").fetchall()]
        # find candle-like table
        candle_table = None
        for t in tables:
            cols = [c[1] for c in con.execute(f"pragma table_info({t})").fetchall()]
            if "symbol" in cols and "timeframe" in cols and "ts_ms" in cols:
                candle_table = t
                break
        out = {"tables": tables[:40], "candle_table": candle_table}
        if candle_table:
            rows = con.execute(
                f"select symbol, count(*), min(ts_ms), max(ts_ms) from {candle_table} "
                f"where timeframe=? and symbol in (?,?,?) group by symbol",
                (TIMEFRAME, *SYMBOLS),
            ).fetchall()
            out["coverage_1h"] = {
                r[0]: {"n": int(r[1]), "min_ts": int(r[2]), "max_ts": int(r[3])} for r in rows
            }
        return out
    finally:
        con.close()


def sim_symbol(db: str, sym: str, cfg: dict, costs) -> dict:
    bars_df = load_ohlcv(db, sym, TIMEFRAME)
    if bars_df is None or bars_df.empty:
        return {"symbol": sym, "status": "no_data", "trades": []}
    touch = load_ohlcv(db, sym, "1m")
    outer = build_outer_folds(int(bars_df["ts_ms"].min()), int(bars_df["ts_ms"].max()), TIMEFRAME, cfg)
    bar_ms = ms_per_bar(TIMEFRAME)
    parts = []
    for fold in outer:
        feat_start = fold.test_start_ms - WARMUP * bar_ms
        window = bars_df[(bars_df["ts_ms"] >= feat_start) & (bars_df["ts_ms"] < fold.test_end_ms)].copy()
        if window.empty:
            continue
        feat = build_signal_frame(window.reset_index(drop=True))
        mask = feat["ts_ms"].to_numpy(np.int64) < fold.test_start_ms
        feat.loc[mask, "long_signal"] = False
        feat.loc[mask, "short_signal"] = False
        parts.append(feat[feat["ts_ms"] >= fold.test_start_ms].copy())
    if not parts:
        return {"symbol": sym, "status": "no_oos_parts", "trades": [], "n_folds": len(outer)}
    stitched = (
        pd.concat(parts, ignore_index=True)
        .drop_duplicates(subset=["ts_ms"])
        .sort_values("ts_ms")
        .reset_index(drop=True)
    )
    signals = to_tradesim_signals(stitched, sym, MAX_HOLD)
    t0 = int(stitched["ts_ms"].min())
    t1 = int(stitched["ts_ms"].max()) + bar_ms
    touch_slice = touch[(touch["ts_ms"] >= t0) & (touch["ts_ms"] < t1)] if touch is not None and not touch.empty else None
    fts = fr = None
    if funding_arrays is not None:
        try:
            fts, fr = funding_arrays(sym)
        except Exception:  # noqa: BLE001
            fts = fr = None
    bars = df_to_barseries(stitched, TIMEFRAME, sym)
    touch_bs = df_to_barseries(touch_slice, "1m", sym) if touch_slice is not None and not touch_slice.empty else None
    try:
        instrument = research_instrument(sym)
    except Exception as exc:  # noqa: BLE001
        return {"symbol": sym, "status": f"instrument_error:{exc}", "trades": []}
    result = simulate(
        bars=bars,
        signals=signals,
        instrument=instrument,
        costs=costs,
        margin=research_margin(leverage=1.0),
        sizing=research_sizing(),
        sim=research_sim(starting_equity=PROJECT_STARTING_EQUITY_USDT),
        touch_bars=touch_bs,
        mark_bars=bars,
        funding_ts_ms=fts,
        funding_rate=fr,
        run_id=f"tsm_chandelier_{sym.lower()}_monthly",
        attach_stamp=True,
    )
    trades = []
    for t in result.trades:
        # entry/exit timestamps
        entry_ms = int(getattr(t, "entry_ts_ms", None) or getattr(t, "open_ts_ms", None) or 0)
        exit_ms = int(getattr(t, "exit_ts_ms", None) or getattr(t, "close_ts_ms", None) or entry_ms)
        trades.append(
            {
                "symbol": sym,
                "side": int(t.side),
                "entry_ts_ms": entry_ms,
                "exit_ts_ms": exit_ms,
                "realized_pnl": float(t.realized_pnl),
            }
        )
    pnls = np.asarray([x["realized_pnl"] for x in trades], dtype=float)
    gp = float(pnls[pnls > 0].sum()) if pnls.size else 0.0
    gl = float((-pnls[pnls < 0]).sum()) if pnls.size else 0.0
    pf = (gp / gl) if gl > 0 else (float("inf") if gp > 0 else float("nan"))
    return {
        "symbol": sym,
        "status": "ok",
        "n_folds": len(outer),
        "oos_start_ms": int(outer[0].test_start_ms) if outer else None,
        "oos_end_ms": int(outer[-1].test_end_ms) if outer else None,
        "n_trades": len(trades),
        "net_pnl": float(pnls.sum()) if pnls.size else 0.0,
        "pooled_pf": float(pf),
        "liquidation_status": str(getattr(result, "liquidation_status", "UNKNOWN")),
        "trades": trades,
    }


def monthly_table(trades: list[dict], oos_start_ms: int, oos_end_ms: int) -> pd.DataFrame:
    if oos_start_ms is None or oos_end_ms is None:
        return pd.DataFrame()
    # month bins covering full OOS calendar (UTC)
    start = pd.Timestamp(oos_start_ms, unit="ms", tz="UTC").to_period("M")
    end = pd.Timestamp(max(oos_end_ms - 1, oos_start_ms), unit="ms", tz="UTC").to_period("M")
    months = pd.period_range(start, end, freq="M")
    if not trades:
        return pd.DataFrame(
            {
                "month": [str(m) for m in months],
                "n_trades": [0] * len(months),
                "net_pnl": [0.0] * len(months),
            }
        )
    df = pd.DataFrame(trades)
    df["month"] = pd.to_datetime(df["entry_ts_ms"], unit="ms", utc=True).dt.to_period("M").astype(str)
    g = df.groupby("month").agg(n_trades=("realized_pnl", "size"), net_pnl=("realized_pnl", "sum"))
    out = pd.DataFrame({"month": [str(m) for m in months]}).merge(
        g.reset_index(), on="month", how="left"
    )
    out["n_trades"] = out["n_trades"].fillna(0).astype(int)
    out["net_pnl"] = out["net_pnl"].fillna(0.0).astype(float)
    return out


def main() -> None:
    ensure_artifact_dirs()
    out_dir = REPORTS / "tsm_chandelier"
    out_dir.mkdir(parents=True, exist_ok=True)

    cfg_path = CONFIG_DIR / "search_space_tsm_chandelier_1h.yaml"
    cfg = yaml.safe_load(cfg_path.read_text(encoding="utf-8"))
    signals_path = ROOT / "strategies" / "tsm_chandelier" / "signals.py"
    gate_path = out_dir / "1h_gate_bcd_summary.json"
    oos_path = out_dir / "1h_oos_summary.json"

    frozen_payload = {
        "freeze_id": "tsm_chandelier_1h_shadow_freeze_20260810",
        "frozen_at_utc": datetime.now(timezone.utc).isoformat(),
        "generation_id": cfg.get("generation_id"),
        "strategy_id": STRATEGY_ID,
        "strategy_version": STRATEGY_VERSION,
        "execution_timeframe": TIMEFRAME,
        "symbols_frozen_primary": list(cfg.get("symbols_primary") or ["BTCUSDT", "ETHUSDT"]),
        "symbols_shadow_requested": SYMBOLS,
        "logical_seed": cfg.get("logical_seed"),
        "search_space_yaml": str(cfg_path),
        "hashes": {
            "search_space_tsm_chandelier_1h.yaml": _file_sha256(cfg_path),
            "signals.py": _file_sha256(signals_path),
            "1h_gate_bcd_summary.json": _file_sha256(gate_path) if gate_path.exists() else None,
            "1h_oos_summary.json": _file_sha256(oos_path) if oos_path.exists() else None,
        },
        "sizing": {
            "mode": "research_sizing_min_exchange_qty",
            "leverage": 1.0,
            "starting_equity_usdt": PROJECT_STARTING_EQUITY_USDT,
            "note": "Shadow/micro-live size must stay at min exchange qty until ops + reconciliation pass; do not raise size from this freeze alone.",
        },
        "costs": "tradesim.research_costs() Bybit USDT perp non-VIP taker baseline",
        "evidence_class": "RESEARCH_PROXY_binance_ohlcv_bybit_cost_model",
        "maximum_earned_readiness": "LIVE_STOP / SHADOW_READY",
        "authorization": "NOT_GRANTED_BY_THIS_FILE",
        "dsr_primary_n_trials": 1,
        "dsr_note": "Primary DSR uses only this generation trial_budget_total=1. Other TSM packages must not be folded into this claim.",
    }
    freeze_body = _canonical_json(frozen_payload)
    frozen_payload["package_hash_sha256"] = hashlib.sha256(freeze_body.encode("utf-8")).hexdigest()

    freeze_path = out_dir / "1h_SHADOW_FREEZE.json"
    freeze_path.write_text(json.dumps(frozen_payload, indent=2), encoding="utf-8")

    _load_green_stamp()
    db = research_db()
    cov = symbol_coverage(db)
    print("DB", db)
    print("coverage", json.dumps(cov.get("coverage_1h", {}), indent=2))

    # Use frozen BTC/ETH fold schedule from BTC sample for shared OOS window when possible
    costs = research_costs()
    per_symbol = []
    all_trades = []
    for sym in SYMBOLS:
        print("=== sim", sym, "===")
        # For SOL exploratory: reuse same outer fold yaml keys but built from its own history
        row = sim_symbol(db, sym, cfg, costs)
        print(
            sym,
            row.get("status"),
            "n=",
            row.get("n_trades"),
            "pnl=",
            row.get("net_pnl"),
            "pf=",
            row.get("pooled_pf"),
            "liq=",
            row.get("liquidation_status"),
        )
        trades = row.pop("trades")
        # monthly on this symbol's OOS window
        mt = monthly_table(trades, row.get("oos_start_ms"), row.get("oos_end_ms"))
        row["monthly"] = mt.to_dict(orient="records") if not mt.empty else []
        if not mt.empty:
            zero_months = int((mt["n_trades"] == 0).sum())
            row["months_in_oos"] = int(len(mt))
            row["zero_trade_months"] = zero_months
            row["avg_trades_per_month"] = float(mt["n_trades"].mean())
            row["median_trades_per_month"] = float(mt["n_trades"].median())
            row["max_consecutive_zero_months"] = int(
                (mt["n_trades"].eq(0).astype(int).groupby((mt["n_trades"].ne(0)).cumsum()).cumsum().max())
                if len(mt)
                else 0
            )
            # better consecutive zeros
            z = mt["n_trades"].to_numpy()
            best = cur = 0
            for v in z:
                if v == 0:
                    cur += 1
                    best = max(best, cur)
                else:
                    cur = 0
            row["max_consecutive_zero_months"] = int(best)
        per_symbol.append(row)
        for t in trades:
            all_trades.append(t)

    # Combined monthly over intersection of OOS if BTC/ETH available
    btc = next((x for x in per_symbol if x["symbol"] == "BTCUSDT" and x.get("status") == "ok"), None)
    eth = next((x for x in per_symbol if x["symbol"] == "ETHUSDT" and x.get("status") == "ok"), None)
    sol = next((x for x in per_symbol if x["symbol"] == "SOLUSDT"), None)

    combined_trades = [t for t in all_trades if t["symbol"] in ("BTCUSDT", "ETHUSDT")]
    if btc:
        comb_mt = monthly_table(combined_trades, btc["oos_start_ms"], btc["oos_end_ms"])
    else:
        comb_mt = pd.DataFrame()

    summary = {
        "freeze_path": str(freeze_path),
        "package_hash_sha256": frozen_payload["package_hash_sha256"],
        "db": db,
        "coverage": cov.get("coverage_1h", {}),
        "per_symbol": per_symbol,
        "btc_eth_combined_monthly": comb_mt.to_dict(orient="records") if not comb_mt.empty else [],
        "btc_eth_avg_trades_per_month": float(comb_mt["n_trades"].mean()) if not comb_mt.empty else None,
        "btc_eth_zero_trade_months": int((comb_mt["n_trades"] == 0).sum()) if not comb_mt.empty else None,
        "sol_status": None if sol is None else {k: sol[k] for k in sol if k != "monthly"},
        "readiness_note": {
            "BTCUSDT_ETHUSDT": "Inside frozen SHADOW_READY package (historical).",
            "SOLUSDT": (
                "NOT in frozen primary symbols; exploratory only. "
                "Adding SOL requires a new preregistered generation before claiming readiness."
            ),
        },
    }
    # consecutive zeros for combined
    if not comb_mt.empty:
        z = comb_mt["n_trades"].to_numpy()
        best = cur = 0
        for v in z:
            if v == 0:
                cur += 1
                best = max(best, cur)
            else:
                cur = 0
        summary["btc_eth_max_consecutive_zero_months"] = int(best)

    sum_path = out_dir / "1h_monthly_trade_distribution.json"
    sum_path.write_text(json.dumps(summary, indent=2, default=str), encoding="utf-8")

    # CSV for easy view
    if not comb_mt.empty:
        comb_mt.to_csv(out_dir / "1h_btc_eth_monthly_trades.csv", index=False)
    for row in per_symbol:
        mt = pd.DataFrame(row.get("monthly") or [])
        if not mt.empty:
            mt.to_csv(out_dir / f"1h_{row['symbol'].lower()}_monthly_trades.csv", index=False)

    print("Wrote", freeze_path)
    print("package_hash", frozen_payload["package_hash_sha256"])
    print("Wrote", sum_path)
    if not comb_mt.empty:
        print("BTC+ETH avg trades/month", float(comb_mt["n_trades"].mean()))
        print("BTC+ETH zero months", int((comb_mt["n_trades"] == 0).sum()), "/", len(comb_mt))
        print(comb_mt.to_string(index=False))


if __name__ == "__main__":
    main()
