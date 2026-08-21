"""Baseline RESEARCH_PROXY backtest for RSI momentum + Fib H0."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tradesim.ensure_source import prefer_botsgeneral_tradesim

prefer_botsgeneral_tradesim()

from engine.data_loader import load_ohlcv, research_db
from engine.tradesim_adapter import df_to_barseries, PROJECT_STARTING_EQUITY_USDT
from tradesim import run_backtest
from strategies.tsm_rsi_momentum_fib.signals import (
    STRATEGY_ID,
    STRATEGY_VERSION,
    build_signal_frame,
    to_tradesim_signals,
)


def run_symbol(symbol: str) -> dict:
    db = research_db()
    bars_df = load_ohlcv(db, symbol, "15m")
    touch = load_ohlcv(db, symbol, "1m")
    feat = build_signal_frame(bars_df)
    signals = to_tradesim_signals(feat, symbol)
    if not signals:
        return {"symbol": symbol, "n_trades": 0, "status": "no_signals", "readiness": "LIVE_STOP / RESEARCH_ONLY"}
    bars = df_to_barseries(feat, "15m", symbol)
    touch_bars = df_to_barseries(touch, "1m", symbol) if not touch.empty else None
    bundle = run_backtest(
        strategy_id=f"{STRATEGY_ID}_{symbol.lower()}",
        strategy_version=STRATEGY_VERSION,
        bars=bars,
        symbol=symbol,
        signals=signals,
        touch_bars=touch_bars,
        starting_equity=PROJECT_STARTING_EQUITY_USDT,
        plot=False,
        print_headline=True,
        store_path=None,
    )
    m = bundle.metrics
    return {
        "symbol": symbol,
        "n_trades": int(m.n_trades),
        "n_signals": len(signals),
        "net_pnl": float(m.net_pnl),
        "profit_factor": float(m.profit_factor),
        "sharpe_ann": float(m.sharpe.annualised) if m.sharpe else 0.0,
        "max_drawdown": float(m.max_drawdown_pct),
        "win_rate": float(m.win_rate),
        "status": "ok",
        "readiness": "LIVE_STOP / RESEARCH_ONLY",
        "evidence_class": "RESEARCH_PROXY",
        "headline": bundle.headline,
    }


def main() -> None:
    out_dir = ROOT / "artifacts" / "reports" / "tsm_rsi_momentum_fib"
    out_dir.mkdir(parents=True, exist_ok=True)
    print("=== tsm_rsi_momentum_fib H0 ===")
    print("Maximum earned readiness: LIVE_STOP / RESEARCH_ONLY")
    print("Evidence class: RESEARCH_PROXY\n")
    results = []
    for sym in ("BTCUSDT", "ETHUSDT"):
        print(f"--- {sym} ---")
        m = run_symbol(sym)
        results.append(m)
        print(
            f"  n_trades={m.get('n_trades')} PF={m.get('profit_factor')} "
            f"SharpeAnn={m.get('sharpe_ann')} status={m.get('status')}"
        )
    path = out_dir / "baseline_h0.json"
    path.write_text(json.dumps(results, indent=2, default=str), encoding="utf-8")
    print("Wrote", path)


if __name__ == "__main__":
    main()
