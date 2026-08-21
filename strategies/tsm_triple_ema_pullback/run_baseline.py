"""Baseline RESEARCH_PROXY backtest for triple-EMA pullback H0 on 15m and 1h."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tradesim.ensure_source import prefer_botsgeneral_tradesim

prefer_botsgeneral_tradesim()

from engine.data_loader import load_ohlcv, research_db
from engine.tradesim_adapter import PROJECT_STARTING_EQUITY_USDT, df_to_barseries
from tradesim import run_backtest
from strategies.tsm_triple_ema_pullback.signals import (
    STRATEGY_ID,
    STRATEGY_VERSION,
    build_signal_frame,
    to_tradesim_signals,
)


def run_one(symbol: str, timeframe: str) -> dict:
    db = research_db()
    bars_df = load_ohlcv(db, symbol, timeframe)
    touch_tf = "1m"
    touch = load_ohlcv(db, symbol, touch_tf)
    feat = build_signal_frame(bars_df)
    hold = 64 if timeframe == "15m" else 48
    signals = to_tradesim_signals(feat, symbol, max_hold_bars=hold)
    if not signals:
        return {
            "symbol": symbol,
            "timeframe": timeframe,
            "n_trades": 0,
            "status": "no_signals",
            "readiness": "LIVE_STOP / RESEARCH_ONLY",
        }
    bars = df_to_barseries(feat, timeframe, symbol)
    touch_bars = df_to_barseries(touch, touch_tf, symbol) if not touch.empty else None
    bundle = run_backtest(
        strategy_id=f"{STRATEGY_ID}_{symbol.lower()}_{timeframe}",
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
        "timeframe": timeframe,
        "n_trades": int(m.n_trades),
        "n_signals": len(signals),
        "net_pnl": float(m.net_pnl),
        "expectancy": float(m.expectancy) if m.n_trades else 0.0,
        "profit_factor": float(m.profit_factor),
        "sharpe_ann": float(m.sharpe.annualised) if m.sharpe else 0.0,
        "hac_sharpe_ann": float(m.sharpe.hac_annualised) if m.sharpe else 0.0,
        "max_drawdown": float(m.max_drawdown_pct),
        "win_rate": float(m.win_rate),
        "fees": float(getattr(m, "total_fees", getattr(m, "fees_paid", 0.0)) or 0.0),
        "status": "ok",
        "readiness": "LIVE_STOP / RESEARCH_ONLY",
        "evidence_class": "RESEARCH_PROXY",
        "headline": bundle.headline,
    }


def main() -> None:
    out_dir = ROOT / "artifacts" / "reports" / "tsm_triple_ema_pullback"
    out_dir.mkdir(parents=True, exist_ok=True)
    print("=== tsm_triple_ema_pullback H0 ===")
    print("Maximum earned readiness: LIVE_STOP / RESEARCH_ONLY\n")
    results = []
    for tf in ("15m", "1h"):
        for sym in ("BTCUSDT", "ETHUSDT"):
            print(f"--- {sym} {tf} ---")
            m = run_one(sym, tf)
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
