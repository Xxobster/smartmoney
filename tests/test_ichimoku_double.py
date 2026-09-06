"""Tests for double Ichimoku (lagged daily bias + 4-hour Chikou) H0."""

from __future__ import annotations

import numpy as np
import pandas as pd

from strategies.common.ichimoku import WARMUP_DOUBLE, build_ichimoku_signal_frame
from strategies.ichimoku_chikou.signals import build_signal_frame as build_single
from strategies.ichimoku_double.signals import WARMUP, build_signal_frame, to_tradesim_signals


def _synthetic(n: int = 900) -> pd.DataFrame:
    rng = np.random.default_rng(22)
    close = 100.0 + np.cumsum(rng.normal(0.04, 0.8, size=n))
    high = close + rng.uniform(0.2, 1.4, size=n)
    low = close - rng.uniform(0.2, 1.4, size=n)
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
    assert WARMUP == WARMUP_DOUBLE


def test_warmup_masks():
    feat = build_signal_frame(_synthetic(WARMUP + 80))
    assert not feat["long_signal"].iloc[:WARMUP].any()
    assert not feat["short_signal"].iloc[:WARMUP].any()


def test_sides_separated():
    feat = build_signal_frame(_synthetic(1000))
    longs = to_tradesim_signals(feat, "BTCUSDT", side_mode="long")
    shorts = to_tradesim_signals(feat, "BTCUSDT", side_mode="short")
    assert all(s.side == 1 for s in longs)
    assert all(s.side == -1 for s in shorts)


def test_truncation_stable():
    df = _synthetic(1100)
    full = build_signal_frame(df)
    n = 900
    trunc = build_signal_frame(df.iloc[:n].reset_index(drop=True))
    cut = n - 48
    assert np.array_equal(
        full["long_signal"].iloc[:cut].to_numpy(),
        trunc["long_signal"].iloc[:cut].to_numpy(),
    )


def test_daily_bias_is_a_filter_not_a_new_entry():
    df = _synthetic(1000)
    single = build_single(df)
    double = build_signal_frame(df)
    assert (double["long_signal"] & ~single["long_signal"]).sum() == 0
    assert (double["short_signal"] & ~single["short_signal"]).sum() == 0


def test_shared_flag_matches_pack():
    df = _synthetic(700)
    a = build_signal_frame(df)
    b = build_ichimoku_signal_frame(df, require_daily_bias=True)
    assert np.array_equal(a["long_signal"].to_numpy(), b["long_signal"].to_numpy())
    assert np.array_equal(a["short_signal"].to_numpy(), b["short_signal"].to_numpy())
