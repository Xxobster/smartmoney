from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tradesim.ensure_source import prefer_botsgeneral_tradesim

prefer_botsgeneral_tradesim()

from data.instrument_specs import get_instrument_spec
from engine.data_loader import load_ohlcv, research_db
from engine.tradesim_adapter import PROJECT_STARTING_EQUITY_USDT, df_to_barseries
from strategies.coinquant_regime_adx.signals import (
    STRATEGY_ID,
    STRATEGY_VERSION,
    build_signal_frame,
    to_tradesim_signals,
)
from tradesim import InstrumentSpec, run_backtest
from tradesim.venue import InstrumentCache


def local_instrument(symbol: str) -> InstrumentSpec:
    try:
        return InstrumentCache().instrument_spec(
            symbol, refresh_if_missing=False, max_age_ms=10**18
        )
    except Exception:
        snap = get_instrument_spec(symbol)
        return InstrumentSpec(
            symbol=symbol,
            tick_size=snap.tick_size,
            qty_step=snap.qty_step,
            min_qty=snap.min_qty,
            min_notional=snap.min_notional,
            max_leverage=snap.max_leverage,
            maintenance_rate=snap.maintenance_margin_rate,
            source="local_instrument_specs_snapshot",
        )


def run_one(symbol: str, timeframe: str) -> dict:
    db = research_db()
    bars_df = load_ohlcv(db, symbol, timeframe)
    if bars_df.empty:
        return {
            "symbol": symbol,
            "timeframe": timeframe,
            "status": "no_data",
            "n_trades": 0,
            "readiness": "LIVE_STOP / RESEARCH_ONLY",
        }
    touch = load_ohlcv(db, symbol, "1m")
    feat = build_signal_frame(bars_df)
    signals = to_tradesim_signals(feat, symbol, max_hold_bars=96)
    if not signals:
        return {
            "symbol": symbol,
            "timeframe": timeframe,
            "n_trades": 0,
            "status": "no_signals",
            "readiness": "LIVE_STOP / RESEARCH_ONLY",
        }
    bundle = run_backtest(
        strategy_id=f"{STRATEGY_ID}_{symbol.lower()}_{timeframe}",
        strategy_version=STRATEGY_VERSION,
        bars=df_to_barseries(feat, timeframe, symbol),
        symbol=symbol,
        instrument=local_instrument(symbol),
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
    out_dir = ROOT / "artifacts" / "reports" / "coinquant_regime_adx"
    out_dir.mkdir(parents=True, exist_ok=True)
    print("=== coinquant_regime_adx H0 ===\nMaximum earned readiness: LIVE_STOP / RESEARCH_ONLY\n")
    results = []
    for sym in ("BTCUSDT", "ETHUSDT"):
        print(f"--- {sym} 1h ---")
        m = run_one(sym, "1h")
        results.append(m)
        print(
            f"  n={m.get('n_trades')} PF={m.get('profit_factor')} "
            f"WR={m.get('win_rate')} status={m.get('status')}"
        )
    path = out_dir / "baseline_h0.json"
    path.write_text(json.dumps(results, indent=2, default=str), encoding="utf-8")
    print("Wrote", path)


if __name__ == "__main__":
    main()
