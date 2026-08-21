#!/usr/bin/env python3
"""tsm_chandelier 1h: full-history metrics + last-6-month trades/finplot.

Usage:
  python strategies/tsm_chandelier/run_1h_report_and_plot.py
  python strategies/tsm_chandelier/run_1h_report_and_plot.py --plot
  python strategies/tsm_chandelier/run_1h_report_and_plot.py --symbol BTCUSDT --plot
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tradesim.ensure_source import prefer_botsgeneral_tradesim

prefer_botsgeneral_tradesim()

from engine.data_loader import load_ohlcv, research_db
from engine.tradesim_adapter import PROJECT_STARTING_EQUITY_USDT, df_to_barseries
from strategies.tsm_chandelier.signals import (
    STRATEGY_ID,
    STRATEGY_VERSION,
    build_signal_frame,
    to_tradesim_signals,
)
from tradesim import run_backtest

OUT = ROOT / "artifacts" / "reports" / "tsm_chandelier" / "1h_full"
MAX_HOLD = 36
SYMBOLS = ("BTCUSDT", "ETHUSDT", "SOLUSDT")
# Last 6 months from today (2026-08-13): 2026-02-13 UTC
LAST6_START_MS = int(datetime(2026, 2, 13, tzinfo=timezone.utc).timestamp() * 1000)


def _utc(ms: int | None) -> str | None:
    if ms is None:
        return None
    return datetime.fromtimestamp(int(ms) / 1000, timezone.utc).isoformat()


def _trade_rows(bundle) -> list[dict]:
    rows = []
    for t in getattr(bundle.result, "trades", ()) or ():
        rows.append(
            {
                "trade_id": int(getattr(t, "trade_id", 0) or 0),
                "symbol": t.symbol,
                "side": "long" if int(t.side) > 0 else "short",
                "entry_ts_ms": int(t.entry_ts_ms),
                "exit_ts_ms": int(t.exit_ts_ms) if t.exit_ts_ms is not None else None,
                "entry_ts_utc": _utc(t.entry_ts_ms),
                "exit_ts_utc": _utc(t.exit_ts_ms),
                "entry_price": float(t.entry_price),
                "exit_price": float(t.exit_price) if t.exit_price is not None else None,
                "stop_price": float(t.stop_price) if t.stop_price is not None else None,
                "target_price": float(t.target_price) if t.target_price is not None else None,
                "qty": float(t.qty),
                "hold_bars": int(getattr(t, "hold_bars", 0) or 0),
                "exit_reason": t.exit_reason,
                "gross_pnl": float(t.gross_pnl),
                "realized_pnl": float(t.realized_pnl),
                "fees": float(t.fees),
                "slippage_cost": float(t.slippage_cost),
                "funding": float(t.funding),
                "mae": float(getattr(t, "mae", 0) or 0),
                "mfe": float(getattr(t, "mfe", 0) or 0),
            }
        )
    return rows


def _compact_metrics(m) -> dict:
    sh = m.sharpe
    return {
        "n_trades": int(m.n_trades),
        "n_longs": int(m.n_longs),
        "n_shorts": int(m.n_shorts),
        "start_utc": _utc(m.start_ts_ms),
        "end_utc": _utc(m.end_ts_ms),
        "span_days": float(m.span_days),
        "trades_per_month": float(m.trades_per_month),
        "net_pnl": float(m.net_pnl),
        "ending_equity": float(m.ending_equity),
        "return_on_invested": float(m.return_on_invested),
        "total_return": float(m.total_return),
        "profit_factor": float(m.profit_factor),
        "win_rate": float(m.win_rate) if m.n_trades else None,
        "expectancy": float(m.expectancy),
        "payoff_ratio": float(getattr(m, "payoff_ratio", float("nan"))),
        "sharpe_ann": float(sh.annualised) if sh else None,
        "hac_sharpe_ann": float(sh.hac_annualised) if sh else None,
        "sortino_ann": float(m.sortino_annualised),
        "max_drawdown_pct": float(m.max_drawdown_pct),
        "max_drawdown_duration_days": float(m.max_drawdown_duration_days),
        "exposure": float(m.exposure),
        "total_fees": float(m.total_fees),
        "total_slippage": float(m.total_slippage),
        "total_funding": float(m.total_funding),
        "n_exits_tp": int(m.n_exits_tp),
        "n_exits_sl": int(m.n_exits_sl),
        "n_exits_other": int(m.n_exits_other),
        "long_pnl": float(m.long_pnl),
        "short_pnl": float(m.short_pnl),
        "avg_hold_hours": float(m.avg_hold_hours),
        "liquidations": int(getattr(m, "n_liquidations", 0) or 0),
        "wallet_blown": bool(m.wallet_blown),
        "buy_hold_return": float(m.buy_hold_return),
    }


def run_full(symbol: str) -> dict:
    db = research_db()
    bars_df = load_ohlcv(db, symbol, "1h")
    if bars_df.empty:
        return {"symbol": symbol, "status": "no_data"}
    feat = build_signal_frame(bars_df)
    signals = to_tradesim_signals(feat, symbol, max_hold_bars=MAX_HOLD)
    rid = f"{STRATEGY_ID}_{symbol.lower()}_1h_full"
    bundle = run_backtest(
        strategy_id=rid,
        strategy_version=STRATEGY_VERSION,
        run_id=rid,
        bars=df_to_barseries(feat, "1h", symbol),
        symbol=symbol,
        signals=signals,
        touch_bars=None,
        starting_equity=PROJECT_STARTING_EQUITY_USDT,
        plot=False,
        print_headline=True,
        store_path=None,
    )
    trades = _trade_rows(bundle)
    last6 = [t for t in trades if int(t["entry_ts_ms"]) >= LAST6_START_MS]
    compact = _compact_metrics(bundle.metrics)
    compact["n_trades_last_6m"] = len(last6)
    compact["net_pnl_last_6m"] = float(sum(t["realized_pnl"] for t in last6))
    return {
        "symbol": symbol,
        "status": "ok",
        "bars_n": int(len(feat)),
        "bars_start_utc": _utc(int(feat["ts_ms"].iloc[0])),
        "bars_end_utc": _utc(int(feat["ts_ms"].iloc[-1])),
        "n_signals": len(signals),
        "metrics": compact,
        "headline": bundle.headline,
        "trades_all": trades,
        "trades_last_6m": last6,
        "feat": feat,
        "signals": signals,
    }


def plot_last6(symbol: str, feat: pd.DataFrame, signals: list) -> None:
    plot_df = feat[feat["ts_ms"] >= LAST6_START_MS].reset_index(drop=True)
    plot_sigs = [s for s in signals if int(s.ts_ms) >= LAST6_START_MS]
    print(
        f"\n=== FINPLOT {symbol} last 6 months "
        f"{_utc(LAST6_START_MS)} -> {_utc(int(plot_df['ts_ms'].iloc[-1]) if len(plot_df) else None)} "
        f"bars={len(plot_df)} signals={len(plot_sigs)} ==="
    )
    if plot_df.empty:
        print("no bars in last-6-month window")
        return
    run_backtest(
        strategy_id=f"{STRATEGY_ID}_{symbol.lower()}_1h_last6",
        strategy_version=STRATEGY_VERSION,
        bars=df_to_barseries(plot_df, "1h", symbol),
        symbol=symbol,
        signals=plot_sigs,
        touch_bars=None,
        starting_equity=PROJECT_STARTING_EQUITY_USDT,
        plot=True,
        print_headline=True,
        store_path=None,
    )


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--symbol", choices=(*SYMBOLS, "ALL"), default="ALL")
    ap.add_argument("--plot", action="store_true", help="Open last-6-month Finplot (blocks until closed)")
    args = ap.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    symbols = SYMBOLS if args.symbol == "ALL" else (args.symbol,)
    print("Maximum earned readiness: LIVE_STOP / RESEARCH_ONLY")
    print("Evidence class: RESEARCH_PROXY (Binance 1h, Bybit cost model, no 1m touch)")
    print(f"Last-6-month trades from {_utc(LAST6_START_MS)}")
    summary = []
    cached = {}
    for sym in symbols:
        print(f"\n--- FULL HISTORY {sym} ---")
        out = run_full(sym)
        cached[sym] = out
        if out.get("status") != "ok":
            print(sym, out)
            continue
        m = out["metrics"]
        print(
            f"  bars {out['bars_start_utc']} -> {out['bars_end_utc']} n={out['bars_n']} "
            f"trades={m['n_trades']} last6={m['n_trades_last_6m']}"
        )
        sym_dir = OUT / sym
        sym_dir.mkdir(parents=True, exist_ok=True)
        (sym_dir / "metrics_full.json").write_text(json.dumps(m, indent=2), encoding="utf-8")
        (sym_dir / "headline.txt").write_text(out["headline"], encoding="utf-8")
        pd.DataFrame(out["trades_all"]).to_csv(sym_dir / "trades_all.csv", index=False)
        (sym_dir / "trades_all.json").write_text(json.dumps(out["trades_all"], indent=2), encoding="utf-8")
        pd.DataFrame(out["trades_last_6m"]).to_csv(sym_dir / "trades_last_6m.csv", index=False)
        (sym_dir / "trades_last_6m.json").write_text(
            json.dumps(out["trades_last_6m"], indent=2), encoding="utf-8"
        )
        summary.append(
            {
                "symbol": sym,
                "status": "ok",
                "bars_start_utc": out["bars_start_utc"],
                "bars_end_utc": out["bars_end_utc"],
                "metrics": m,
            }
        )
    report = {
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "maximum_earned_readiness": "LIVE_STOP / RESEARCH_ONLY",
        "evidence_class": "RESEARCH_PROXY_binance_1h_bybit_cost_model",
        "note": (
            "Full-history 1h path (research_ohlcv.sqlite). BTC/ETH have no 1m in research DB; "
            "SOL 1m is incomplete. SOL is exploratory and not inside the frozen BTC+ETH SHADOW_READY claim. "
            "Last-6-month trade list is a slice of the full-history run, not a new selection."
        ),
        "last_6m_start_utc": _utc(LAST6_START_MS),
        "symbols": summary,
    }
    (OUT / "summary.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print("WROTE", OUT / "summary.json")
    if args.plot:
        for sym in symbols:
            out = cached.get(sym) or {}
            if out.get("status") != "ok":
                continue
            plot_last6(sym, out["feat"], out["signals"])


if __name__ == "__main__":
    main()
