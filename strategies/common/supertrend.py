"""Causal SuperTrend line and direction (one pass; path-dependent like Parabolic SAR)."""

from __future__ import annotations

import numpy as np
import pandas as pd


def supertrend_line_dir(
    high: np.ndarray,
    low: np.ndarray,
    close: np.ndarray,
    *,
    atr_n: int,
    multiplier: float,
) -> tuple[np.ndarray, np.ndarray]:
    """Return (line, direction) with direction +1 below price (uptrend), -1 above (downtrend)."""
    n = len(close)
    line = np.full(n, np.nan)
    direction = np.zeros(n, dtype=np.int8)
    if n == 0:
        return line, direction
    prev_c = np.roll(close, 1)
    prev_c[0] = close[0]
    tr = np.maximum(high - low, np.maximum(np.abs(high - prev_c), np.abs(low - prev_c)))
    atr = pd.Series(tr).ewm(alpha=1.0 / atr_n, adjust=False, min_periods=atr_n).mean().to_numpy(
        float
    )
    hl2 = (high + low) / 2.0
    basic_ub = hl2 + multiplier * atr
    basic_lb = hl2 - multiplier * atr
    fu = np.copy(basic_ub)
    fl = np.copy(basic_lb)
    start = int(atr_n)
    direction[:start] = 0
    for i in range(start, n):
        prev_fu = fu[i - 1]
        prev_fl = fl[i - 1]
        fu[i] = basic_ub[i] if (basic_ub[i] < prev_fu or close[i - 1] > prev_fu) else prev_fu
        fl[i] = basic_lb[i] if (basic_lb[i] > prev_fl or close[i - 1] < prev_fl) else prev_fl
        if close[i] > fu[i - 1]:
            direction[i] = 1
        elif close[i] < fl[i - 1]:
            direction[i] = -1
        else:
            direction[i] = direction[i - 1]
        line[i] = fl[i] if direction[i] == 1 else fu[i]
    return line, direction
