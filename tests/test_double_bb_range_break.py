"""Tests for Double Bollinger inner-range break H0."""

from __future__ import annotations

import numpy as np
import pandas as pd

from strategies.double_bb_range_break.signals import (
    WARMUP,
    build_signal_frame,
    to_tradesim_signals,
)


def _synthetic(n: int = 80) -> pd.DataFrame:
    rng = np.random.default_rng(31)
    close = 100.0 + np.cumsum(rng.normal(0.0, 0.4, size=n))
    high = close + rng.uniform(0.1, 0.6, size=n)
    low = close - rng.uniform(0.1, 0.6, size=n)
    ts = np.arange(n, dtype=np.int64) * 900_000
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
    assert (feat["bb_inner_up"].iloc[WARMUP:] >= feat["bb_mid"].iloc[WARMUP:]).all()
    assert (feat["bb_inner_dn"].iloc[WARMUP:] <= feat["bb_mid"].iloc[WARMUP:]).all()


def test_sides_separated():
    feat = build_signal_frame(_synthetic(200))
    longs = to_tradesim_signals(feat, "BTCUSDT", side_mode="long")
    shorts = to_tradesim_signals(feat, "BTCUSDT", side_mode="short")
    assert all(s.side == 1 for s in longs)
    assert all(s.side == -1 for s in shorts)


def test_truncation_stable():
    df = _synthetic(180)
    full = build_signal_frame(df)
    trunc = build_signal_frame(df.iloc[:140].reset_index(drop=True))
    assert np.array_equal(
        full["short_signal"].iloc[:140].to_numpy(),
        trunc["short_signal"].to_numpy(),
    )
