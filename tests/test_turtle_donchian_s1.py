"""Tests for Turtle Donchian System 1 H0."""

from __future__ import annotations

import numpy as np
import pandas as pd

from strategies.turtle_donchian_s1.signals import DONCHIAN_N, build_signal_frame, to_tradesim_signals


def _synthetic(n: int = 100) -> pd.DataFrame:
    rng = np.random.default_rng(1)
    close = 100.0 + np.cumsum(rng.normal(0.0, 1.0, size=n))
    high = close + rng.uniform(0.2, 1.5, size=n)
    low = close - rng.uniform(0.2, 1.5, size=n)
    ts = np.arange(n, dtype=np.int64) * 86_400_000
    return pd.DataFrame(
        {
            "ts_ms": ts,
            "open": close,
            "high": high,
            "low": low,
            "close": close,
            "volume": np.ones(n),
        }
    )


def test_prior_channel_is_shifted():
    feat = build_signal_frame(_synthetic(80))
    assert feat["donchian_prior_high"].iloc[:DONCHIAN_N].isna().all()


def test_sides_separated():
    feat = build_signal_frame(_synthetic(150))
    longs = to_tradesim_signals(feat, "BTCUSDT", side_mode="long")
    shorts = to_tradesim_signals(feat, "BTCUSDT", side_mode="short")
    assert all(s.side == 1 for s in longs)
    assert all(s.side == -1 for s in shorts)


def test_truncation_stable():
    df = _synthetic(120)
    full = build_signal_frame(df)
    trunc = build_signal_frame(df.iloc[:90].reset_index(drop=True))
    assert np.array_equal(
        full["long_signal"].iloc[:90].to_numpy(),
        trunc["long_signal"].to_numpy(),
    )
