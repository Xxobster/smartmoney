"""Tests for Quant Tactics Donchian + ADX H0."""

from __future__ import annotations

import numpy as np
import pandas as pd

from strategies.quant_tactics_donchian_adx.signals import (
    DONCHIAN_N,
    WARMUP,
    build_signal_frame,
    to_tradesim_signals,
)


def _synthetic(n: int = 250) -> pd.DataFrame:
    rng = np.random.default_rng(3)
    close = 100.0 + np.cumsum(rng.normal(0.0, 0.6, size=n))
    high = close + rng.uniform(0.2, 1.2, size=n)
    low = close - rng.uniform(0.2, 1.2, size=n)
    ts = np.arange(n, dtype=np.int64) * 3_600_000
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


def test_prior_channel_shifted():
    feat = build_signal_frame(_synthetic(80))
    assert feat["donchian_prior_high"].iloc[:DONCHIAN_N].isna().all()


def test_warmup_masks():
    feat = build_signal_frame(_synthetic(200))
    assert not feat["long_signal"].iloc[:WARMUP].any()
    assert not feat["short_signal"].iloc[:WARMUP].any()


def test_sides_separated():
    feat = build_signal_frame(_synthetic(300))
    longs = to_tradesim_signals(feat, "ETHUSDT", side_mode="long")
    shorts = to_tradesim_signals(feat, "ETHUSDT", side_mode="short")
    assert all(s.side == 1 for s in longs)
    assert all(s.side == -1 for s in shorts)


def test_truncation_stable():
    df = _synthetic(280)
    full = build_signal_frame(df)
    trunc = build_signal_frame(df.iloc[:220].reset_index(drop=True))
    assert np.array_equal(
        full["long_signal"].iloc[:220].to_numpy(),
        trunc["long_signal"].to_numpy(),
    )
