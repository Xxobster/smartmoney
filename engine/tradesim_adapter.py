"""Adapter: SMC feature/signals -> botsgeneral tradesim engine."""
from __future__ import annotations

from dataclasses import asdict
from typing import Any, Optional

import numpy as np
import pandas as pd

from tradesim import BarSeries, Signal, run_backtest
from tradesim.research.defaults import RESEARCH_STARTING_EQUITY_USDT

# Project profile freezes 10_000 USDT; tradesim package default (100) cannot
# open BTCUSDT min size under the 60% margin-utilisation cap at 1x.
PROJECT_STARTING_EQUITY_USDT = 10_000.0


TF_MS = {
    "1m": 60_000,
    "5m": 300_000,
    "15m": 900_000,
    "30m": 1_800_000,
    "1h": 3_600_000,
    "4h": 14_400_000,
    "1d": 86_400_000,
}


def df_to_barseries(df: pd.DataFrame, timeframe: str, symbol: str) -> BarSeries:
    return BarSeries(
        ts_ms=df["ts_ms"].to_numpy(dtype=np.int64),
        open=df["open"].to_numpy(dtype=float),
        high=df["high"].to_numpy(dtype=float),
        low=df["low"].to_numpy(dtype=float),
        close=df["close"].to_numpy(dtype=float),
        volume=df["volume"].to_numpy(dtype=float) if "volume" in df.columns else None,
        timeframe_ms=TF_MS[timeframe],
        symbol=symbol,
    )


def features_to_signals(
    feat: pd.DataFrame,
    symbol: str,
    *,
    target_rr: float = 3.0,
    stop_beyond_sweep_atr_mult: float = 0.1,
    use_pd_targets: bool = True,
    max_hold_bars: int = 96,
    risk_fraction: float | None = None,
) -> list[Signal]:
    """Build causal tradesim Signals from scored SMC feature frame.

    One signal per closed bar when long XOR short fires. Stop/target as absolute
    prices from the decision bar (also used live) — or offsets when absolute
    levels are unavailable.
    """
    if feat.empty:
        return []
    signals: list[Signal] = []
    ts = feat["ts_ms"].to_numpy(np.int64)
    close = feat["close"].to_numpy(float)
    high = feat["high"].to_numpy(float)
    low = feat["low"].to_numpy(float)
    long_sig = feat["long_signal"].to_numpy(bool)
    short_sig = feat["short_signal"].to_numpy(bool)
    atr = feat["atr"].to_numpy(float) if "atr" in feat.columns else np.full(len(feat), np.nan)
    sweep = (
        feat["sweep_extreme"].to_numpy(float)
        if "sweep_extreme" in feat.columns
        else np.full(len(feat), np.nan)
    )
    pd_q25 = feat["pd_q25"].to_numpy(float) if "pd_q25" in feat.columns else np.full(len(feat), np.nan)
    pd_q50 = feat["pd_q50"].to_numpy(float) if "pd_q50" in feat.columns else np.full(len(feat), np.nan)
    pd_q75 = feat["pd_q75"].to_numpy(float) if "pd_q75" in feat.columns else np.full(len(feat), np.nan)

    for i in range(len(feat)):
        if long_sig[i] and not short_sig[i]:
            side = 1
        elif short_sig[i] and not long_sig[i]:
            side = -1
        else:
            continue
        a = atr[i] if not np.isnan(atr[i]) else max(high[i] - low[i], close[i] * 0.001)
        if side == 1:
            extreme = sweep[i] if not np.isnan(sweep[i]) else low[i]
            stop = float(extreme - stop_beyond_sweep_atr_mult * a)
            if use_pd_targets and not np.isnan(pd_q50[i]):
                target = float(pd_q75[i] if not np.isnan(pd_q75[i]) else pd_q50[i])
            else:
                risk = max(close[i] - stop, close[i] * 1e-4)
                target = float(close[i] + target_rr * risk)
        else:
            extreme = sweep[i] if not np.isnan(sweep[i]) else high[i]
            stop = float(extreme + stop_beyond_sweep_atr_mult * a)
            if use_pd_targets and not np.isnan(pd_q50[i]):
                target = float(pd_q25[i] if not np.isnan(pd_q25[i]) else pd_q50[i])
            else:
                risk = max(stop - close[i], close[i] * 1e-4)
                target = float(close[i] - target_rr * risk)

        # Skip inverted levels
        if side == 1 and not (stop < close[i] < target):
            continue
        if side == -1 and not (target < close[i] < stop):
            continue

        signals.append(
            Signal(
                ts_ms=int(ts[i]),
                side=side,
                symbol=symbol,
                stop_price=stop,
                target_price=target,
                max_hold_bars=int(max_hold_bars),
                risk_fraction=risk_fraction,
                tag="smc",
            )
        )
    return signals


def run_tradesim_on_features(
    feat: pd.DataFrame,
    symbol: str,
    timeframe: str,
    *,
    target_rr: float = 3.0,
    stop_beyond_sweep_atr_mult: float = 0.1,
    use_pd_targets: bool = True,
    max_hold_bars: int = 96,
    risk_fraction: float | None = None,
    funding_ts_ms: Optional[np.ndarray] = None,
    funding_rate: Optional[np.ndarray] = None,
    touch_df: Optional[pd.DataFrame] = None,
    touch_timeframe: Optional[str] = None,
    starting_equity: float = PROJECT_STARTING_EQUITY_USDT,
    strategy_id: str = "smc_gen2",
    print_headline: bool = False,
) -> dict[str, Any]:
    """Run canonical tradesim backtest; return metrics dict."""
    if feat.empty or len(feat) < 10:
        return {
            "n_trades": 0,
            "expectancy": -1e9,
            "net_pnl": 0.0,
            "profit_factor": 0.0,
            "gross_profit": 0.0,
            "gross_loss": 0.0,
            "status": "insufficient_bars",
        }

    bars = df_to_barseries(feat, timeframe, symbol)
    signals = features_to_signals(
        feat,
        symbol,
        target_rr=target_rr,
        stop_beyond_sweep_atr_mult=stop_beyond_sweep_atr_mult,
        use_pd_targets=use_pd_targets,
        max_hold_bars=max_hold_bars,
        risk_fraction=risk_fraction,
    )
    if not signals:
        return {
            "n_trades": 0,
            "n_signals": 0,
            "expectancy": 0.0,
            "net_pnl": 0.0,
            "profit_factor": float("nan"),
            "gross_profit": 0.0,
            "gross_loss": 0.0,
            "sharpe_ann": 0.0,
            "max_drawdown": 0.0,
            "status": "no_signals",
        }

    touch_bars = None
    if touch_df is not None and touch_timeframe and not touch_df.empty:
        touch_bars = df_to_barseries(touch_df, touch_timeframe, symbol)

    bundle = run_backtest(
        strategy_id=strategy_id,
        strategy_version="gen2",
        bars=bars,
        symbol=symbol,
        signals=signals,
        touch_bars=touch_bars,
        funding_ts_ms=funding_ts_ms,
        funding_rate=funding_rate,
        starting_equity=starting_equity,
        plot=False,
        print_headline=print_headline,
        store_path=None,
    )
    m = bundle.metrics
    n_trades = int(m.n_trades)
    net = float(m.net_pnl)
    exp = float(m.expectancy) if n_trades else 0.0
    pf = float(m.profit_factor)
    sharpe = float(m.sharpe.annualised) if m.sharpe is not None else 0.0
    hac = float(m.sharpe.hac_annualised) if m.sharpe is not None else 0.0
    mdd = float(m.max_drawdown_pct)
    wr = float(m.win_rate)
    # Gross profit / loss for true multi-symbol / multi-fold pooling (V2)
    trade_pnls = np.asarray(
        [float(t.realized_pnl) for t in getattr(bundle.result, "trades", ())],
        dtype=float,
    )
    gross_profit = float(trade_pnls[trade_pnls > 0].sum()) if trade_pnls.size else 0.0
    gross_loss = float((-trade_pnls[trade_pnls < 0]).sum()) if trade_pnls.size else 0.0
    return {
        "n_trades": n_trades,
        "n_signals": len(signals),
        "net_pnl": net,
        "expectancy": exp,
        "profit_factor": pf,
        "gross_profit": gross_profit,
        "gross_loss": gross_loss,
        "sharpe_ann": sharpe,
        "hac_sharpe_ann": hac,
        "max_drawdown": mdd,
        "win_rate": wr,
        "wallet_blown": bool(bundle.wallet_blown),
        "fees": float(getattr(m, "total_fees", getattr(m, "fees_paid", 0.0)) or 0.0),
        "funding": float(getattr(m, "total_funding", getattr(m, "funding_pnl", 0.0)) or 0.0),
        "headline": bundle.headline,
        "status": "ok",
        "engine": "tradesim",
        "evidence_class": "RESEARCH_PROXY_binance_ohlcv_bybit_cost_model",
    }
