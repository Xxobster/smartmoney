"""Vectorized weighted and Hull moving averages (no Python loops over bars)."""

from __future__ import annotations

import numpy as np
from numpy.lib.stride_tricks import sliding_window_view


def rolling_wma(x: np.ndarray, n: int) -> np.ndarray:
    """Causal weighted moving average. Weight 1..n, heaviest on the last bar."""
    n = int(n)
    arr = np.asarray(x, dtype=np.float64)
    out = np.full(arr.shape[0], np.nan, dtype=np.float64)
    if n <= 0 or arr.size < n:
        return out
    w = np.arange(1, n + 1, dtype=np.float64)
    w = w / w.sum()
    out[n - 1 :] = sliding_window_view(arr, n) @ w
    return out


def hull_moving_average(close: np.ndarray, n: int = 16) -> np.ndarray:
    """Alan Hull (2005) default length is 16. Nested weighted averages, causal."""
    n = int(n)
    half = max(n // 2, 1)
    sqrt_n = max(int(round(float(n) ** 0.5)), 1)
    raw = 2.0 * rolling_wma(close, half) - rolling_wma(close, n)
    return rolling_wma(raw, sqrt_n)
