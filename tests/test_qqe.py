"""Tests for QQE MOD helper."""

from __future__ import annotations

import numpy as np

from strategies.common.qqe import qqe_mod_zero_line


def test_uptrend_line_goes_positive():
    close = 50.0 + np.linspace(0.0, 40.0, 80)
    line = qqe_mod_zero_line(close)
    assert np.isfinite(line[40:]).all()
    assert (line[50:] > 0.0).all()


def test_truncation_stable():
    rng = np.random.default_rng(4)
    close = 100.0 + np.cumsum(rng.normal(0.02, 0.4, size=120))
    full = qqe_mod_zero_line(close)
    trunc = qqe_mod_zero_line(close[:90])
    assert np.allclose(full[:90], trunc, equal_nan=True)
