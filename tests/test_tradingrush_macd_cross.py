"""Unit test: MACD cross below zero is causal."""

from __future__ import annotations

import numpy as np
import pandas as pd

from strategies.tradingrush_macd_cross.signals import SMA_SLOW, build_signal_frame


def test_no_signal_before_warmup():
    n = SMA_SLOW + 20
    close = np.linspace(100.0, 110.0, n)
    df = pd.DataFrame(
        {
            "ts_ms": np.arange(n, dtype=np.int64) * 3_600_000,
            "open": close,
            "high": close + 0.5,
            "low": close - 0.5,
            "close": close,
        }
    )
    feat = build_signal_frame(df)
    assert int(feat["long_signal"].iloc[:SMA_SLOW].sum()) == 0


def test_features_have_no_future_shift():
    n = SMA_SLOW + 40
    rng = np.random.default_rng(1)
    close = 100 + np.cumsum(rng.normal(0, 0.5, n))
    df = pd.DataFrame(
        {
            "ts_ms": np.arange(n, dtype=np.int64) * 3_600_000,
            "open": close,
            "high": close + 0.4,
            "low": close - 0.4,
            "close": close,
        }
    )
    full = build_signal_frame(df)
    truncated = build_signal_frame(df.iloc[:-8].copy())
    overlap = len(truncated)
    assert np.array_equal(
        full["long_signal"].iloc[:overlap].to_numpy(),
        truncated["long_signal"].to_numpy(),
    )
