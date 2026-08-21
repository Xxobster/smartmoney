"""Unit test: Bollinger close-break is causal and vectorized."""

from __future__ import annotations

import numpy as np
import pandas as pd

from strategies.tradingrush_bb_breakout.signals import BB_PERIOD, SMA_SLOW, build_signal_frame


def test_no_signal_before_warmup_and_first_cross_only():
    n = SMA_SLOW + 40
    close = np.full(n, 100.0)
    close[SMA_SLOW + 10 :] = 130.0
    df = pd.DataFrame(
        {
            "ts_ms": np.arange(n, dtype=np.int64) * 3_600_000,
            "open": close,
            "high": close + 1.0,
            "low": close - 1.0,
            "close": close,
        }
    )
    feat = build_signal_frame(df)
    assert int(feat["long_signal"].iloc[:SMA_SLOW].sum()) == 0
    fires = np.flatnonzero(feat["long_signal"].to_numpy())
    assert len(fires) == 1
    assert int(fires[0]) == SMA_SLOW + 10


def test_features_have_no_future_shift():
    n = SMA_SLOW + 30
    rng = np.random.default_rng(0)
    close = 100 + np.cumsum(rng.normal(0, 0.4, n))
    df = pd.DataFrame(
        {
            "ts_ms": np.arange(n, dtype=np.int64) * 3_600_000,
            "open": close,
            "high": close + 0.5,
            "low": close - 0.5,
            "close": close,
        }
    )
    full = build_signal_frame(df)
    truncated = build_signal_frame(df.iloc[:-5].copy())
    overlap = len(truncated)
    assert np.array_equal(
        full["long_signal"].iloc[:overlap].to_numpy(),
        truncated["long_signal"].to_numpy(),
    )
