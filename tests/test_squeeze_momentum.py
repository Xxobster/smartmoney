"""Tests for LazyBear Squeeze Momentum helper."""

from __future__ import annotations

import numpy as np

from strategies.common.squeeze_momentum import squeeze_momentum


def test_uptrend_positive():
    n = 80
    close = 50.0 + np.linspace(0.0, 40.0, n)
    high = close + 0.4
    low = close - 0.4
    val = squeeze_momentum(high, low, close)
    assert np.isfinite(val[40:]).all()
    assert (val[50:] > 0.0).all()


def test_truncation_stable():
    rng = np.random.default_rng(8)
    close = 100.0 + np.cumsum(rng.normal(0.02, 0.4, size=120))
    high = close + 0.8
    low = close - 0.8
    full = squeeze_momentum(high, low, close)
    trunc = squeeze_momentum(high[:90], low[:90], close[:90])
    assert np.allclose(full[:90], trunc, equal_nan=True)
