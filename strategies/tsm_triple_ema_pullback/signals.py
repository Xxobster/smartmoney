"""Vectorized triple-EMA pullback continuation signals (causal)."""

from __future__ import annotations

import numpy as np
import pandas as pd

from tradesim import Signal

STRATEGY_ID = "tsm_triple_ema_pullback"
STRATEGY_VERSION = "0.1.0"


def ema(close: np.ndarray, length: int) -> np.ndarray:
    return pd.Series(close).ewm(span=length, adjust=False).mean().to_numpy(dtype=float)


def build_signal_frame(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy().reset_index(drop=True)
    close = out["close"].to_numpy(float)
    high = out["high"].to_numpy(float)
    low = out["low"].to_numpy(float)
    e20 = ema(close, 20)
    e100 = ema(close, 100)
    e200 = ema(close, 200)
    out["ema20"] = e20
    out["ema100"] = e100
    out["ema200"] = e200

    slope_up = e100 > np.roll(e100, 3)
    slope_dn = e100 < np.roll(e100, 3)
    slope_up[:3] = False
    slope_dn[:3] = False

    bull = (close > e20) & (e20 > e100) & (e100 > e200) & slope_up
    bear = (close < e20) & (e20 < e100) & (e100 < e200) & slope_dn

    # Space between 100 and 200 not contracting (absolute gap vs 5 bars ago)
    gap = np.abs(e100 - e200)
    gap_prev = np.roll(gap, 5)
    gap_prev[:5] = np.nan
    space_ok = gap >= (gap_prev * 0.98)

    touch100 = (low <= e100) & (high >= e100)
    long_rej = bull & space_ok & touch100 & (close > e100) & (close > out["open"].to_numpy(float))
    short_rej = bear & space_ok & touch100 & (close < e100) & (close < out["open"].to_numpy(float))

    # One signal per touch cluster: require prior bar not already in signal
    long_sig = long_rej & ~np.roll(long_rej, 1)
    short_sig = short_rej & ~np.roll(short_rej, 1)
    long_sig[0] = short_sig[0] = False

    stop = np.full(len(out), np.nan)
    target = np.full(len(out), np.nan)
    stop[long_sig] = np.minimum(low[long_sig], e100[long_sig]) * (1 - 1e-4)
    risk_l = np.maximum(close[long_sig] - stop[long_sig], close[long_sig] * 1e-4)
    target[long_sig] = close[long_sig] + 2.0 * risk_l
    stop[short_sig] = np.maximum(high[short_sig], e100[short_sig]) * (1 + 1e-4)
    risk_s = np.maximum(stop[short_sig] - close[short_sig], close[short_sig] * 1e-4)
    target[short_sig] = close[short_sig] - 2.0 * risk_s

    out["bull_align"] = bull
    out["bear_align"] = bear
    out["long_signal"] = long_sig
    out["short_signal"] = short_sig
    out["stop_price"] = stop
    out["target_price"] = target
    return out


def to_tradesim_signals(feat: pd.DataFrame, symbol: str, max_hold_bars: int = 64) -> list[Signal]:
    signals: list[Signal] = []
    ts = feat["ts_ms"].to_numpy(np.int64)
    for i in range(len(feat)):
        if bool(feat["long_signal"].iloc[i]) and not bool(feat["short_signal"].iloc[i]):
            side = 1
        elif bool(feat["short_signal"].iloc[i]) and not bool(feat["long_signal"].iloc[i]):
            side = -1
        else:
            continue
        sp = float(feat["stop_price"].iloc[i])
        tp = float(feat["target_price"].iloc[i])
        if np.isnan(sp) or np.isnan(tp):
            continue
        signals.append(
            Signal(
                ts_ms=int(ts[i]),
                side=side,
                symbol=symbol,
                stop_price=sp,
                target_price=tp,
                max_hold_bars=max_hold_bars,
                tag="tsm_3ema",
            )
        )
    return signals
