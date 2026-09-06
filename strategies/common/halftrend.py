"""Everget HalfTrend (causal). Path-dependent; one pass like Parabolic SAR.

Defaults: amplitude 2, channel deviation 2, Average True Range 100.
https://www.tradingview.com/script/U1SJ8ubc-HalfTrend/
"""

from __future__ import annotations

import numpy as np
import pandas as pd


def halftrend_trend(
    high: np.ndarray,
    low: np.ndarray,
    close: np.ndarray,
    *,
    amplitude: int = 2,
    channel_deviation: float = 2.0,
    atr_n: int = 100,
) -> np.ndarray:
    """Return trend: 0 = up (blue arrow), 1 = down (red arrow). Early bars 0."""
    n = len(close)
    trend = np.zeros(n, dtype=np.int8)
    if n == 0:
        return trend
    # Channel ATR(100)×deviation is Everget's plot band; arrows use amplitude only.
    _ = (channel_deviation, atr_n)
    amp = max(int(amplitude), 1)
    high_price = pd.Series(high).rolling(amp, min_periods=amp).max().to_numpy(float)
    low_price = pd.Series(low).rolling(amp, min_periods=amp).min().to_numpy(float)
    highma = pd.Series(high).rolling(amp, min_periods=amp).mean().to_numpy(float)
    lowma = pd.Series(low).rolling(amp, min_periods=amp).mean().to_numpy(float)
    next_trend = np.zeros(n, dtype=np.int8)
    max_low = np.zeros(n, dtype=np.float64)
    min_high = np.zeros(n, dtype=np.float64)
    max_low[0] = float(low[0])
    min_high[0] = float(high[0])
    start = max(amp, 1)
    for i in range(1, n):
        if next_trend[i - 1] == 1:
            prev_lp = low_price[i - 1]
            max_low[i] = max(
                float(prev_lp) if np.isfinite(prev_lp) else max_low[i - 1],
                max_low[i - 1],
            )
            hm = highma[i]
            if (
                np.isfinite(hm)
                and hm < max_low[i]
                and close[i] < low[i - 1]
            ):
                trend[i] = 1
                next_trend[i] = 0
                hp = high_price[i]
                min_high[i] = float(hp) if np.isfinite(hp) else high[i]
            else:
                trend[i] = trend[i - 1]
                next_trend[i] = next_trend[i - 1]
                min_high[i] = min_high[i - 1]
        else:
            prev_hp = high_price[i - 1]
            min_high[i] = min(
                float(prev_hp) if np.isfinite(prev_hp) else min_high[i - 1],
                min_high[i - 1],
            )
            lm = lowma[i]
            if (
                np.isfinite(lm)
                and lm > min_high[i]
                and close[i] > high[i - 1]
            ):
                trend[i] = 0
                next_trend[i] = 1
                lp = low_price[i]
                max_low[i] = float(lp) if np.isfinite(lp) else low[i]
            else:
                trend[i] = trend[i - 1]
                next_trend[i] = next_trend[i - 1]
                max_low[i] = max_low[i - 1]
    trend[:start] = 0
    return trend
