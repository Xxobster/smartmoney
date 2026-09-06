"""Tests for single-timeframe Ichimoku Chikou-break H0."""

from __future__ import annotations

import numpy as np
import pandas as pd

from strategies.common.ichimoku import WARMUP_LTF, shift_nan
from strategies.ichimoku_chikou.signals import WARMUP, build_signal_frame, to_tradesim_signals


def _synthetic(n: int = 400) -> pd.DataFrame:
    rng = np.random.default_rng(21)
    close = 100.0 + np.cumsum(rng.normal(0.03, 0.7, size=n))
    high = close + rng.uniform(0.2, 1.2, size=n)
    low = close - rng.uniform(0.2, 1.2, size=n)
    ts = np.arange(n, dtype=np.int64) * 14_400_000
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


def test_warmup_constant_matches_common():
    assert WARMUP == WARMUP_LTF


def test_warmup_masks():
    feat = build_signal_frame(_synthetic(WARMUP + 80))
    assert not feat["long_signal"].iloc[:WARMUP].any()
    assert not feat["short_signal"].iloc[:WARMUP].any()


def test_sides_separated():
    feat = build_signal_frame(_synthetic(500))
    longs = to_tradesim_signals(feat, "BTCUSDT", side_mode="long")
    shorts = to_tradesim_signals(feat, "BTCUSDT", side_mode="short")
    assert all(s.side == 1 for s in longs)
    assert all(s.side == -1 for s in shorts)


def test_truncation_stable():
    df = _synthetic(420)
    full = build_signal_frame(df)
    n = 360
    trunc = build_signal_frame(df.iloc[:n].reset_index(drop=True))
    cut = n - 8
    assert np.array_equal(
        full["long_signal"].iloc[:cut].to_numpy(),
        trunc["long_signal"].iloc[:cut].to_numpy(),
    )


def test_cloud_is_displaced_not_current_senkou():
    df = _synthetic(200)
    feat = build_signal_frame(df)
    tenkan = feat["tenkan"].to_numpy(float)
    kijun = feat["kijun"].to_numpy(float)
    expected_a = shift_nan((tenkan + kijun) * 0.5, 26)
    got = feat["cloud_a"].to_numpy(float)
    both = np.isfinite(expected_a) & np.isfinite(got)
    assert both.sum() > 50
    np.testing.assert_allclose(got[both], expected_a[both])


def test_chikou_break_uses_past_high_not_future():
    df = _synthetic(180)
    feat = build_signal_frame(df)
    c = feat["close"].to_numpy(float)
    h = feat["high"].to_numpy(float)
    up = feat["chikou_break_up"].to_numpy(bool)
    idx = np.flatnonzero(up)
    assert len(idx) > 0
    i = int(idx[len(idx) // 2])
    assert c[i] > h[i - 26]
    assert c[i - 1] <= h[i - 27]
