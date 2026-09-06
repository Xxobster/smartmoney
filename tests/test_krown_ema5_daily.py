"""Tests for Krown 5 Exponential Moving Average daily H0."""

from __future__ import annotations

import numpy as np
import pandas as pd

from strategies.krown_ema5_daily.signals import (
    WARMUP,
    build_signal_frame,
    build_signal_frame_papercut,
    to_tradesim_signals,
)


def _synthetic(n: int = 80) -> pd.DataFrame:
    rng = np.random.default_rng(2)
    close = 100.0 + np.cumsum(rng.normal(0.05, 1.5, size=n))
    high = close + rng.uniform(0.4, 2.0, size=n)
    low = close - rng.uniform(0.4, 2.0, size=n)
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


def test_papercut_is_stricter():
    df = _synthetic(120)
    raw = build_signal_frame(df)["long_signal"].sum()
    cut = build_signal_frame_papercut(df)["long_signal"].sum()
    assert cut <= raw


def test_short_mirror_sides():
    feat = build_signal_frame(_synthetic(100))
    shorts = to_tradesim_signals(feat, "BTCUSDT", side_mode="short_mirror")
    assert all(s.side == -1 for s in shorts)


def test_truncation_stable():
    df = _synthetic(90)
    full = build_signal_frame(df)
    trunc = build_signal_frame(df.iloc[:70].reset_index(drop=True))
    assert np.array_equal(
        full["long_signal"].iloc[:70].to_numpy(),
        trunc["long_signal"].to_numpy(),
    )
