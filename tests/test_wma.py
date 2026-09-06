"""Tests for vectorized weighted / Hull moving averages."""

from __future__ import annotations

import numpy as np

from strategies.common.wma import hull_moving_average, rolling_wma


def test_wma_matches_weighted_dot():
    x = np.array([1.0, 2.0, 3.0, 4.0, 5.0])
    n = 3
    w = np.array([1.0, 2.0, 3.0])
    w = w / w.sum()
    got = rolling_wma(x, n)
    assert np.isnan(got[0]) and np.isnan(got[1])
    assert np.isclose(got[2], float(x[:3] @ w))
    assert np.isclose(got[4], float(x[2:] @ w))


def test_hull_constant_series_is_constant_after_warmup():
    x = np.full(40, 10.0)
    h = hull_moving_average(x, 16)
    assert np.isnan(h[:15]).all()
    assert np.allclose(h[20:], 10.0)


def test_hull_truncation_stable():
    rng = np.random.default_rng(3)
    x = 100.0 + np.cumsum(rng.normal(0.0, 0.5, size=80))
    full = hull_moving_average(x, 16)
    trunc = hull_moving_average(x[:50], 16)
    assert np.allclose(full[:50], trunc, equal_nan=True)
