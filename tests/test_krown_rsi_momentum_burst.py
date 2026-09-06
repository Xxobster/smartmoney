"""Tests for Krown hourly Relative Strength Index momentum-burst H0."""

from __future__ import annotations

import numpy as np
import pandas as pd

from strategies.krown_rsi_momentum_burst.signals import (
    WARMUP,
    build_signal_frame,
    to_tradesim_signals,
)


def _synthetic(n: int = 2000) -> pd.DataFrame:
    rng = np.random.default_rng(3)
    close = 100.0 + np.cumsum(rng.normal(0.02, 0.8, size=n))
    high = close + rng.uniform(0.1, 0.9, size=n)
    low = close - rng.uniform(0.1, 0.9, size=n)
    ts = np.arange(n, dtype=np.int64) * 3_600_000
    return pd.DataFrame(
        {
            "ts_ms": ts,
            "open": close - rng.uniform(-0.2, 0.2, size=n),
            "high": np.maximum(high, close),
            "low": np.minimum(low, close),
            "close": close,
            "volume": rng.uniform(10, 100, size=n),
        }
    )


def test_warmup_masks():
    feat = build_signal_frame(_synthetic(900))
    assert not feat["long_signal"].iloc[:WARMUP].any()
    assert not feat["short_signal"].iloc[:WARMUP].any()


def test_short_mirror_sides():
    feat = build_signal_frame(_synthetic(1200))
    shorts = to_tradesim_signals(feat, "BTCUSDT", side_mode="short_mirror")
    assert all(s.side == -1 for s in shorts)
    assert all(s.stop_price is None for s in shorts)
    assert all(s.max_hold_bars == 24 for s in shorts)


def test_truncation_stable():
    df = _synthetic(1600)
    full = build_signal_frame(df)
    trunc = build_signal_frame(df.iloc[:1200].reset_index(drop=True))
    n = 1200 - 48
    assert np.array_equal(
        full["long_signal"].iloc[:n].to_numpy(),
        trunc["long_signal"].iloc[:n].to_numpy(),
    )
