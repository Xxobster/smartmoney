"""Tests for Heikin Ashi × Bollinger H0."""

from __future__ import annotations

import numpy as np
import pandas as pd

from strategies.heikin_ashi_bb_stoch.signals import WARMUP, build_signal_frame, to_tradesim_signals


def _synthetic(n: int = 400) -> pd.DataFrame:
    rng = np.random.default_rng(7)
    close = 100.0 + np.cumsum(rng.normal(0.0, 0.4, size=n))
    high = close + rng.uniform(0.1, 0.9, size=n)
    low = close - rng.uniform(0.1, 0.9, size=n)
    ts = np.arange(n, dtype=np.int64) * 3_600_000
    return pd.DataFrame(
        {
            "ts_ms": ts,
            "open": close - rng.uniform(-0.2, 0.2, size=n),
            "high": high,
            "low": low,
            "close": close,
            "volume": rng.uniform(10, 100, size=n),
        }
    )


def test_warmup_masks_early_bars():
    feat = build_signal_frame(_synthetic(250))
    assert not feat["long_signal"].iloc[:WARMUP].any()
    assert not feat["short_signal"].iloc[:WARMUP].any()


def test_sides_separated():
    feat = build_signal_frame(_synthetic(500))
    longs = to_tradesim_signals(feat, "BTCUSDT", side_mode="long")
    shorts = to_tradesim_signals(feat, "BTCUSDT", side_mode="short")
    assert all(s.side == 1 for s in longs)
    assert all(s.side == -1 for s in shorts)


def test_truncation_stable():
    df = _synthetic(400)
    full = build_signal_frame(df)
    trunc = build_signal_frame(df.iloc[:320].reset_index(drop=True))
    assert np.array_equal(
        full["long_signal"].iloc[:320].to_numpy(),
        trunc["long_signal"].to_numpy(),
    )


def test_heikin_ashi_causal_open():
    feat = build_signal_frame(_synthetic(80))
    ha_o = feat["ha_open"].to_numpy(float)
    ha_c = feat["ha_close"].to_numpy(float)
    o = feat["open"].to_numpy(float)
    c = feat["close"].to_numpy(float)
    assert np.isclose(ha_o[0], 0.5 * (o[0] + c[0]))
    assert np.isclose(ha_o[1], 0.5 * (ha_o[0] + ha_c[0]))
