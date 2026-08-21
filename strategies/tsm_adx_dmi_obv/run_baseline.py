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
from strategies.tsm_adx_dmi_obv.signals import (
    STRATEGY_ID,
    STRATEGY_VERSION,
    build_signal_frame,
    to_tradesim_signals,
)


def run_one(symbol: str, timeframe: str) -> dict:
    db = research_db()
    bars_df = load_ohlcv(db, symbol, timeframe)
    if bars_df.empty:
        return {"symbol": symbol, "timeframe": timeframe, "status": "no_data", "n_trades": 0,
                "readiness": "LIVE_STOP / RESEARCH_ONLY"}
    touch = load_ohlcv(db, symbol, "1m")
    feat = build_signal_frame(bars_df)
    hold = 24 if timeframe == "4h" else 20
    signals = to_tradesim_signals(feat, symbol, max_hold_bars=hold)
    if not signals:
        return {"symbol": symbol, "timeframe": timeframe, "n_trades": 0, "status": "no_signals",
                "readiness": "LIVE_STOP / RESEARCH_ONLY"}
    bundle = run_backtest(
        strategy_id=f"{STRATEGY_ID}_{symbol.lower()}_{timeframe}",
        strategy_version=STRATEGY_VERSION,
        bars=df_to_barseries(feat, timeframe, symbol),
        symbol=symbol,
        signals=signals,
        touch_bars=df_to_barseries(touch, "1m", symbol) if not touch.empty else None,
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
        "profit_factor": float(m.profit_factor),
        "sharpe_ann": float(m.sharpe.annualised) if m.sharpe else 0.0,
        "hac_sharpe_ann": float(m.sharpe.hac_annualised) if m.sharpe else 0.0,
        "max_drawdown": float(m.max_drawdown_pct),
        "win_rate": float(m.win_rate),
        "net_pnl": float(m.net_pnl),
        "status": "ok",
        "readiness": "LIVE_STOP / RESEARCH_ONLY",
        "evidence_class": "RESEARCH_PROXY",
        "headline": bundle.headline,
    }


def main() -> None:
    out_dir = ROOT / "artifacts" / "reports" / "tsm_adx_dmi_obv"
    out_dir.mkdir(parents=True, exist_ok=True)
    print("=== tsm_adx_dmi_obv H0 ===\nMaximum earned readiness: LIVE_STOP / RESEARCH_ONLY\n")
    results = []
    for tf in ("4h", "1d"):
        for sym in ("BTCUSDT", "ETHUSDT"):
            print(f"--- {sym} {tf} ---")
            m = run_one(sym, tf)
            results.append(m)
            print(f"  n={m.get('n_trades')} PF={m.get('profit_factor')} WR={m.get('win_rate')} status={m.get('status')}")
    path = out_dir / "baseline_h0.json"
    path.write_text(json.dumps(results, indent=2, default=str), encoding="utf-8")
    print("Wrote", path)


if __name__ == "__main__":
    main()
