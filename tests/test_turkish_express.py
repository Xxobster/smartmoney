"""Tests for Turkish Express H0 (EMA 200 trend)."""

from __future__ import annotations

import numpy as np
import pandas as pd

from strategies.turkish_express.signals import WARMUP, build_signal_frame, to_tradesim_signals


def _synthetic(n: int = 280) -> pd.DataFrame:
    rng = np.random.default_rng(19)
    close = 100.0 + np.cumsum(rng.normal(0.05, 0.8, size=n))
    high = close + rng.uniform(0.2, 1.5, size=n)
    low = close - rng.uniform(0.2, 1.5, size=n)
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
    assert not feat["short_signal"].iloc[:WARMUP].any()
    assert feat["ift"].iloc[WARMUP:].notna().all()


def test_ift_bounded():
    feat = build_signal_frame(_synthetic(320))
    ift = feat["ift"].iloc[WARMUP:].to_numpy(float)
    assert np.nanmax(np.abs(ift)) <= 1.0 + 1e-9


def test_sides_separated():
    feat = build_signal_frame(_synthetic(320))
    longs = to_tradesim_signals(feat, "BTCUSDT", side_mode="long")
    shorts = to_tradesim_signals(feat, "BTCUSDT", side_mode="short")
    assert all(s.side == 1 for s in longs)
    assert all(s.side == -1 for s in shorts)


def test_truncation_stable():
    df = _synthetic(340)
    full = build_signal_frame(df)
    trunc = build_signal_frame(df.iloc[:300].reset_index(drop=True))
    assert np.array_equal(
        full["long_signal"].iloc[:300].to_numpy(),
        trunc["long_signal"].to_numpy(),
    )
