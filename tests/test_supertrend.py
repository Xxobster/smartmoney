"""Tests for shared SuperTrend helper."""

from __future__ import annotations

import numpy as np

from strategies.common.supertrend import supertrend_line_dir


def test_uptrend_series_goes_positive():
    n = 80
    close = 50.0 + np.linspace(0.0, 40.0, n)
    high = close + 0.5
    low = close - 0.5
    line, direction = supertrend_line_dir(high, low, close, atr_n=8, multiplier=4.0)
    assert (direction[40:] == 1).all()
    assert np.isfinite(line[40:]).all()
    assert (close[40:] > line[40:]).all()


def test_truncation_stable():
    rng = np.random.default_rng(2)
    close = 100.0 + np.cumsum(rng.normal(0.02, 0.4, size=120))
    high = close + 0.8
    low = close - 0.8
    full_l, full_d = supertrend_line_dir(high, low, close, atr_n=8, multiplier=4.0)
    trunc_l, trunc_d = supertrend_line_dir(high[:90], low[:90], close[:90], atr_n=8, multiplier=4.0)
    assert np.array_equal(full_d[:90], trunc_d)
    assert np.allclose(full_l[:90], trunc_l, equal_nan=True)
