"""Tests for Turkish Express + Hull 16 mix (pre-registered, not a retune)."""

from __future__ import annotations

import numpy as np
import pandas as pd

from strategies.turkish_express.signals import build_signal_frame as build_ema
from strategies.turkish_express_hma.signals import WARMUP, build_signal_frame, to_tradesim_signals


def _synthetic(n: int = 320) -> pd.DataFrame:
    rng = np.random.default_rng(23)
    close = 100.0 + np.cumsum(rng.normal(0.04, 0.7, size=n))
    high = close + rng.uniform(0.2, 1.2, size=n)
    low = close - rng.uniform(0.2, 1.2, size=n)
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
    feat = build_signal_frame(_synthetic())
    assert not feat["long_signal"].iloc[:WARMUP].any()


def test_mix_differs_from_ema200_trend_line():
    df = _synthetic(360)
    a = build_ema(df)
    b = build_signal_frame(df)
    assert not np.allclose(
        a["trend_line"].iloc[WARMUP:].to_numpy(float),
        b["trend_line"].iloc[WARMUP:].to_numpy(float),
        equal_nan=True,
    )


def test_sides_separated():
    feat = build_signal_frame(_synthetic())
    longs = to_tradesim_signals(feat, "BTCUSDT", side_mode="long")
    shorts = to_tradesim_signals(feat, "BTCUSDT", side_mode="short")
    assert all(s.side == 1 for s in longs)
    assert all(s.side == -1 for s in shorts)


def test_truncation_stable():
    df = _synthetic(340)
    full = build_signal_frame(df)
    trunc = build_signal_frame(df.iloc[:300].reset_index(drop=True))
    assert np.array_equal(
        full["short_signal"].iloc[:300].to_numpy(),
        trunc["short_signal"].to_numpy(),
    )
