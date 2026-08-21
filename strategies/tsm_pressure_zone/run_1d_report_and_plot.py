"""Export full 1d pressure-zone metrics/trades and open Finplot.

Usage:
  python strategies/tsm_pressure_zone/run_1d_report_and_plot.py
  python strategies/tsm_pressure_zone/run_1d_report_and_plot.py --symbol BTCUSDT --plot
  python strategies/tsm_pressure_zone/run_1d_report_and_plot.py --symbol ETHUSDT --plot
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tradesim.ensure_source import prefer_botsgeneral_tradesim

prefer_botsgeneral_tradesim()

from engine.data_loader import load_ohlcv, research_db
from engine.tradesim_adapter import PROJECT_STARTING_EQUITY_USDT, df_to_barseries
from tradesim import run_backtest
from strategies.tsm_pressure_zone.signals import (
    STRATEGY_ID,
    STRATEGY_VERSION,
    build_signal_frame,
    to_tradesim_signals,
)

OUT = ROOT / "artifacts" / "reports" / "tsm_pressure_zone" / "1d_full"


def _trade_rows(bundle) -> list[dict]:
    rows = []
    for t in bundle.result.trades:
        rows.append(
            {
                "trade_id": int(t.trade_id),
                "symbol": t.symbol,
                "side": "long" if int(t.side) > 0 else "short",
                "entry_ts_utc": pd.Timestamp(t.entry_ts_ms, unit="ms", tz="UTC").isoformat(),
                "exit_ts_utc": pd.Timestamp(t.exit_ts_ms, unit="ms", tz="UTC").isoformat(),
                "entry_price": float(t.entry_price),
                "exit_price": float(t.exit_price),
                "stop_price": float(t.stop_price),
                "target_price": float(t.target_price) if t.target_price is not None else None,
                "qty": float(t.qty),
                "hold_bars": int(t.hold_bars),
                "exit_reason": t.exit_reason,
                "gross_pnl": float(t.gross_pnl),
                "realized_pnl": float(t.realized_pnl),
                "fees": float(t.fees),
                "slippage_cost": float(t.slippage_cost),
                "funding": float(t.funding),
                "mae": float(t.mae),
                "mfe": float(t.mfe),
                "return_units": float(t.return_units),
                "entry_bar_exit": bool(t.entry_bar_exit),
                "ambiguous_intrabar": bool(t.ambiguous_intrabar),
                "tag": t.tag,
            }
        )
    return rows


def run_symbol(symbol: str, *, plot: bool) -> dict:
    db = research_db()
    bars_df = load_ohlcv(db, symbol, "1d")
    touch = load_ohlcv(db, symbol, "1m")
    feat = build_signal_frame(bars_df)
    signals = to_tradesim_signals(feat, symbol, max_hold_bars=20)
    rid = f"{STRATEGY_ID}_{symbol.lower()}_1d_full"
    bundle = run_backtest(
        strategy_id=rid,
        strategy_version=STRATEGY_VERSION,
        run_id=rid,
        bars=df_to_barseries(feat, "1d", symbol),
        symbol=symbol,
        signals=signals,
        touch_bars=df_to_barseries(touch, "1m", symbol) if not touch.empty else None,
        starting_equity=PROJECT_STARTING_EQUITY_USDT,
        plot=plot,
        print_headline=True,
        report=True,
        max_zone_trades=500,
        notes="Pressure zone H0 daily full report + trades export",
    )
    m = bundle.metrics.as_dict()
    trades = _trade_rows(bundle)
    sym_dir = OUT / symbol
    sym_dir.mkdir(parents=True, exist_ok=True)
    (sym_dir / "metrics_full.json").write_text(json.dumps(m, indent=2, default=str), encoding="utf-8")
    (sym_dir / "headline.txt").write_text(bundle.headline, encoding="utf-8")
    pd.DataFrame(trades).to_csv(sym_dir / "trades_all.csv", index=False)
    (sym_dir / "trades_all.json").write_text(json.dumps(trades, indent=2), encoding="utf-8")
    meta = {
        "symbol": symbol,
        "timeframe": "1d",
        "strategy_id": STRATEGY_ID,
        "run_id": bundle.run_id,
        "report_dir": bundle.report_dir,
        "n_trades": len(trades),
        "readiness": "LIVE_STOP / RESEARCH_ONLY",
        "evidence_class": "RESEARCH_PROXY",
        "artifacts": {
            "metrics": str(sym_dir / "metrics_full.json"),
            "trades_csv": str(sym_dir / "trades_all.csv"),
            "trades_json": str(sym_dir / "trades_all.json"),
            "headline": str(sym_dir / "headline.txt"),
        },
    }
    (sym_dir / "meta.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")
    print("Wrote", sym_dir)
    return {"meta": meta, "metrics": m, "trades": trades, "headline": bundle.headline}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--symbol", choices=("BTCUSDT", "ETHUSDT", "ALL"), default="ALL")
    ap.add_argument("--plot", action="store_true", help="Open Finplot (blocks until closed)")
    args = ap.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    symbols = ("BTCUSDT", "ETHUSDT") if args.symbol == "ALL" else (args.symbol,)
    summary = []
    for sym in symbols:
        # When plotting ALL, plot only the last symbol interactively after export of both.
        do_plot = bool(args.plot) and args.symbol != "ALL"
        out = run_symbol(sym, plot=do_plot)
        summary.append(
            {
                "symbol": sym,
                "n_trades": out["meta"]["n_trades"],
                "profit_factor": out["metrics"]["profit_factor"],
                "win_rate": out["metrics"]["win_rate"],
                "net_pnl": out["metrics"]["net_pnl"],
                "sharpe_ann": out["metrics"]["sharpe"]["annualised"],
                "report_dir": out["meta"]["report_dir"],
            }
        )
    (OUT / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    if args.plot and args.symbol == "ALL":
        print("Exports done. Re-run with --symbol BTCUSDT --plot (then ETH) to open Finplot.")


if __name__ == "__main__":
    main()
