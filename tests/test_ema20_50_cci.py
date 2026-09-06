"""Tests for 20/50 Exponential Moving Average + CCI H0."""

from __future__ import annotations

import numpy as np
import pandas as pd

from strategies.ema20_50_cci.signals import WARMUP, build_signal_frame, to_tradesim_signals


def _synthetic(n: int = 400) -> pd.DataFrame:
    rng = np.random.default_rng(11)
    close = 100.0 + np.cumsum(rng.normal(0.02, 0.7, size=n))
    high = close + rng.uniform(0.2, 1.0, size=n)
    low = close - rng.uniform(0.2, 1.0, size=n)
    ts = np.arange(n, dtype=np.int64) * 3_600_000
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
    feat = build_signal_frame(_synthetic(WARMUP + 40))
    assert not feat["long_signal"].iloc[:WARMUP].any()


def test_sides_separated():
    feat = build_signal_frame(_synthetic(500))
    longs = to_tradesim_signals(feat, "BTCUSDT", side_mode="long")
    shorts = to_tradesim_signals(feat, "BTCUSDT", side_mode="short")
    assert all(s.side == 1 for s in longs)
    assert all(s.side == -1 for s in shorts)


def test_truncation_stable():
    df = _synthetic(480)
    full = build_signal_frame(df)
    trunc = build_signal_frame(df.iloc[:400].reset_index(drop=True))
    assert np.array_equal(
        full["long_signal"].iloc[:400].to_numpy(),
        trunc["long_signal"].to_numpy(),
    )
