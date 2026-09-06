"""Quantitative Qualitative Estimation (QQE) MOD histogram (RSI MA minus 50).

TradingView QQE MOD public defaults: Relative Strength Index 6, smoothing 5.
Zero-line is that smoothed RSI minus 50. Path-free; fully vectorized.
"""

from __future__ import annotations

import numpy as np
import pandas as pd


def qqe_mod_zero_line(close: np.ndarray, *, rsi_n: int = 6, sf: int = 5) -> np.ndarray:
    """Return smoothed RSI minus 50 (QQE MOD histogram around zero)."""
    d = np.diff(close, prepend=close[0] if len(close) else 0.0)
    up = np.where(d > 0.0, d, 0.0)
    dn = np.where(d < 0.0, -d, 0.0)
    ru = pd.Series(up).ewm(alpha=1.0 / rsi_n, adjust=False, min_periods=rsi_n).mean()
    rd = pd.Series(dn).ewm(alpha=1.0 / rsi_n, adjust=False, min_periods=rsi_n).mean()
    rsi = 100.0 - 100.0 / (1.0 + ru / (rd + 1e-12))
    rsi_ma = rsi.ewm(span=sf, adjust=False, min_periods=sf).mean()
    return (rsi_ma - 50.0).to_numpy(float)
