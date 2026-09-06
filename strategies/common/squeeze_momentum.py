"""LazyBear Squeeze Momentum histogram. Vectorized linear regression last-point fit.

https://www.tradingview.com/script/nqQ1DT5a-Squeeze-Momentum-Indicator-LazyBear/
Defaults: length 20, Bollinger 2.0, Keltner 1.5.
"""

from __future__ import annotations

import numpy as np
import pandas as pd


def _rolling_linreg_last(y: np.ndarray, n: int) -> np.ndarray:
    """Pine ``linreg(src, n, 0)``: fitted value at the last bar of each window."""
    s = pd.Series(y, dtype=float)
    idx = np.arange(len(y), dtype=float)
    sum_y = s.rolling(n, min_periods=n).sum()
    sum_ky = pd.Series(idx * y, dtype=float).rolling(n, min_periods=n).sum()
    t0 = idx - n + 1.0
    sum_xy = sum_ky - t0 * sum_y
    sum_x = n * (n - 1) / 2.0
    sum_x2 = (n - 1) * n * (2 * n - 1) / 6.0
    den = n * sum_x2 - sum_x * sum_x
    slope = (n * sum_xy - sum_x * sum_y) / den
    intercept = (sum_y - slope * sum_x) / n
    return (intercept + slope * (n - 1)).to_numpy(float)


def squeeze_momentum(
    high: np.ndarray,
    low: np.ndarray,
    close: np.ndarray,
    *,
    length: int = 20,
    bb_mult: float = 2.0,
    kc_mult: float = 1.5,
) -> np.ndarray:
    """Return LazyBear momentum (linear regression of close vs midline)."""
    del bb_mult, kc_mult  # squeeze dots unused; histogram uses length only
    hh = pd.Series(high).rolling(length, min_periods=length).max()
    ll = pd.Series(low).rolling(length, min_periods=length).min()
    sma_c = pd.Series(close).rolling(length, min_periods=length).mean()
    mid = ((hh + ll) / 2.0 + sma_c) / 2.0
    src = close - mid.to_numpy(float)
    return _rolling_linreg_last(src, length)
