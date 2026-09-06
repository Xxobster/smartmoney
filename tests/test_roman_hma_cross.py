"""Unit tests for Hull Moving Average close-cross H0."""

from __future__ import annotations

import numpy as np
import pandas as pd

from strategies.roman_hma_cross.signals import (
    WARMUP,
    build_signal_frame,
    to_tradesim_signals,
)


def _synthetic(n: int = 120) -> pd.DataFrame:
    rng = np.random.default_rng(11)
    close = 100.0 + np.cumsum(rng.normal(0.0, 0.5, size=n))
    high = close + rng.uniform(0.1, 0.8, size=n)
    low = close - rng.uniform(0.1, 0.8, size=n)
    ts = np.arange(n, dtype=np.int64) * 3_600_000 * 4
    return pd.DataFrame(
        {
            "ts_ms": ts,
            "open": close,
            "high": np.maximum(high, close),
            "low": np.minimum(low, close),
            "close": close,
            "volume": rng.uniform(1.0, 10.0, size=n),
        }
    )


def test_warmup_masks():
    feat = build_signal_frame(_synthetic())
    assert not feat["long_signal"].iloc[:WARMUP].any()
    assert feat["hma16"].iloc[WARMUP:].notna().all()


def test_long_mode_only_long_signals():
    feat = build_signal_frame(_synthetic(200))
    sigs = to_tradesim_signals(feat, "BTCUSDT", max_hold_bars=48, side_mode="long")
    assert all(s.side == 1 for s in sigs)


def test_short_mirror_only_short_signals():
    feat = build_signal_frame(_synthetic(200))
    sigs = to_tradesim_signals(feat, "BTCUSDT", max_hold_bars=48, side_mode="short_mirror")
    assert all(s.side == -1 for s in sigs)


def test_future_truncation_does_not_change_earlier_features():
    df = _synthetic(180)
    full = build_signal_frame(df)
    trunc = build_signal_frame(df.iloc[:140].reset_index(drop=True))
    cols = ["hma16", "long_signal", "short_signal"]
    for c in cols:
        a = full[c].iloc[:140].to_numpy()
        b = trunc[c].to_numpy()
        if c.endswith("signal"):
            assert np.array_equal(a, b)
        else:
            assert np.allclose(a, b, equal_nan=True)
