"""Tests for weekly + daily Moving Average Convergence Divergence H0."""

from __future__ import annotations

import numpy as np
import pandas as pd

from strategies.financial_wisdom_dual_macd.signals import WARMUP, build_signal_frame, to_tradesim_signals


def _synthetic(n: int = 400) -> pd.DataFrame:
    rng = np.random.default_rng(11)
    close = 100.0 + np.cumsum(rng.normal(0.02, 1.2, size=n))
    high = close + rng.uniform(0.3, 2.0, size=n)
    low = close - rng.uniform(0.3, 2.0, size=n)
    ts = np.arange(n, dtype=np.int64) * 86_400_000
    return pd.DataFrame(
        {
            "ts_ms": ts,
            "open": close,
            "high": np.maximum(high, close),
            "low": np.minimum(low, close),
            "close": close,
            "volume": np.ones(n),
        }
    )


def test_warmup_masks():
    feat = build_signal_frame(_synthetic())
    assert not feat["long_signal"].iloc[:WARMUP].any()
    assert not feat["short_signal"].iloc[:WARMUP].any()


def test_long_and_short_mirror_sides():
    feat = build_signal_frame(_synthetic(500))
    longs = to_tradesim_signals(feat, "BTCUSDT", side_mode="long")
    shorts = to_tradesim_signals(feat, "BTCUSDT", side_mode="short_mirror")
    assert all(s.side == 1 for s in longs)
    assert all(s.side == -1 for s in shorts)


def test_truncation_stable():
    df = _synthetic(420)
    full = build_signal_frame(df)
    trunc = build_signal_frame(df.iloc[:360].reset_index(drop=True))
    assert np.array_equal(
        full["long_signal"].iloc[:360].to_numpy(),
        trunc["long_signal"].to_numpy(),
    )
