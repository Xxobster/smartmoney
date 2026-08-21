"""Causal 200 EMA high/low channel break + retest signals."""

from __future__ import annotations

import numpy as np
import pandas as pd

from tradesim import Signal

STRATEGY_ID = "tsm_ema200_channel_breakout"
STRATEGY_VERSION = "0.1.0"


def ema(series: np.ndarray, length: int) -> np.ndarray:
    return pd.Series(series).ewm(span=length, adjust=False).mean().to_numpy(dtype=float)


def build_signal_frame(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy().reset_index(drop=True)
    close = out["close"].to_numpy(float)
    high = out["high"].to_numpy(float)
    low = out["low"].to_numpy(float)
    open_ = out["open"].to_numpy(float)
    e_hi = ema(high, 200)
    e_lo = ema(low, 200)
    out["ema200_high"] = e_hi
    out["ema200_low"] = e_lo

    n = len(out)
    long_sig = np.zeros(n, dtype=bool)
    short_sig = np.zeros(n, dtype=bool)
    stop = np.full(n, np.nan)
    target = np.full(n, np.nan)

    # Arm on closed-bar break; expire after look_ahead bars
    look = 12
    armed_long_until = -1
    armed_short_until = -1
    for i in range(1, n):
        if close[i - 1] <= e_hi[i - 1] and close[i] > e_hi[i]:
            armed_long_until = i + look
            armed_short_until = -1
        if close[i - 1] >= e_lo[i - 1] and close[i] < e_lo[i]:
            armed_short_until = i + look
            armed_long_until = -1

        if i <= armed_long_until and i > 0:
            # retest: touch channel top from above and reject
            if low[i] <= e_hi[i] <= high[i] and close[i] > e_hi[i] and close[i] > open_[i]:
                long_sig[i] = True
                stop[i] = min(low[i], e_lo[i]) * (1 - 1e-4)
                risk = max(close[i] - stop[i], close[i] * 1e-4)
                target[i] = close[i] + 3.0 * risk
                armed_long_until = -1

        if i <= armed_short_until and i > 0:
            if low[i] <= e_lo[i] <= high[i] and close[i] < e_lo[i] and close[i] < open_[i]:
                short_sig[i] = True
                stop[i] = max(high[i], e_hi[i]) * (1 + 1e-4)
                risk = max(stop[i] - close[i], close[i] * 1e-4)
                target[i] = close[i] - 3.0 * risk
                armed_short_until = -1

    out["long_signal"] = long_sig
    out["short_signal"] = short_sig
    out["stop_price"] = stop
    out["target_price"] = target
    return out


def to_tradesim_signals(feat: pd.DataFrame, symbol: str, max_hold_bars: int = 96) -> list[Signal]:
    out: list[Signal] = []
    ts = feat["ts_ms"].to_numpy(np.int64)
    for i in range(len(feat)):
        if bool(feat["long_signal"].iloc[i]) ^ bool(feat["short_signal"].iloc[i]):
            side = 1 if bool(feat["long_signal"].iloc[i]) else -1
            sp = float(feat["stop_price"].iloc[i])
            tp = float(feat["target_price"].iloc[i])
            if np.isnan(sp) or np.isnan(tp):
                continue
            out.append(
                Signal(
                    ts_ms=int(ts[i]),
                    side=side,
                    symbol=symbol,
                    stop_price=sp,
                    target_price=tp,
                    max_hold_bars=max_hold_bars,
                    tag="tsm_ema200ch",
                )
            )
    return out
