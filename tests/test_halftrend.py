"""Tests for Everget HalfTrend helper."""

from __future__ import annotations

import numpy as np

from strategies.common.halftrend import halftrend_trend


def test_uptrend_series_goes_up():
    n = 80
    close = 50.0 + np.linspace(0.0, 40.0, n)
    high = close + 0.5
    low = close - 0.5
    trend = halftrend_trend(high, low, close)
    assert (trend[40:] == 0).all()


def test_truncation_stable():
    rng = np.random.default_rng(7)
    close = 100.0 + np.cumsum(rng.normal(0.02, 0.4, size=120))
    high = close + 0.8
    low = close - 0.8
    full = halftrend_trend(high, low, close)
    trunc = halftrend_trend(high[:90], low[:90], close[:90])
    assert np.array_equal(full[:90], trunc)
