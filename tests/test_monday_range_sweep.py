"""Causal checks for Monday-range features."""

from __future__ import annotations

import numpy as np
import pandas as pd

from strategies.monday_range_sweep.signals import WARMUP_DAYS, _supertrend_dir, build_signal_frame


def _hourly(start_utc: str, n: int, close: float = 100.0) -> pd.DataFrame:
    start = pd.Timestamp(start_utc, tz="UTC")
    ts = start.value // 1_000_000 + np.arange(n, dtype=np.int64) * 3_600_000
    c = np.full(n, close, dtype=float)
    return pd.DataFrame(
        {
            "ts_ms": ts,
            "open": c,
            "high": c + 1.0,
            "low": c - 1.0,
            "close": c,
        }
    )


def test_monday_range_only_after_monday_closes():
    # 2023-04-03 04:00 UTC = Monday 00:00 New York (Eastern Daylight)
    df = _hourly("2023-04-03T04:00:00Z", 24 * 5, close=100.0)
    ny = pd.to_datetime(df["ts_ms"], unit="ms", utc=True).dt.tz_convert("America/New_York")
    mon = ny.dt.weekday.to_numpy() == 0
    df.loc[mon, "high"] = 110.0
    df.loc[mon, "low"] = 90.0
    feat = build_signal_frame(df)
    assert not np.isfinite(feat.loc[mon, "monday_high"]).any()
    tue = ny.dt.weekday.to_numpy() == 1
    assert np.allclose(feat.loc[tue, "monday_high"].to_numpy(float), 110.0)
    assert np.allclose(feat.loc[tue, "monday_low"].to_numpy(float), 90.0)


def test_no_signal_on_friday_or_saturday():
    df = _hourly("2023-01-02T00:00:00Z", 24 * (WARMUP_DAYS + 21), close=100.0)
    feat = build_signal_frame(df)
    ny = pd.to_datetime(feat["ts_ms"], unit="ms", utc=True).dt.tz_convert("America/New_York")
    weekendish = ny.dt.weekday.isin([4, 5]).to_numpy()
    assert int(feat.loc[weekendish, "long_signal"].sum()) == 0
    assert int(feat.loc[weekendish, "short_signal"].sum()) == 0


def test_supertrend_can_turn_down():
    n = 80
    close = np.concatenate([np.linspace(100, 140, 40), np.linspace(139, 70, 40)])
    high = close + 2.0
    low = close - 2.0
    st = _supertrend_dir(high, low, close)
    assert int((st < 0).sum()) > 0


def test_truncation_does_not_change_earlier_signals():
    df = _hourly("2022-01-03T00:00:00Z", 24 * (WARMUP_DAYS + 40), close=100.0)
    rng = np.random.default_rng(3)
    df["close"] = 100 + np.cumsum(rng.normal(0, 0.8, len(df)))
    df["open"] = df["close"]
    df["high"] = df["close"] + 1.2
    df["low"] = df["close"] - 1.2
    full = build_signal_frame(df)
    truncated = build_signal_frame(df.iloc[:-36].copy())
    overlap = len(truncated)
    assert np.array_equal(
        full["long_signal"].iloc[:overlap].to_numpy(),
        truncated["long_signal"].to_numpy(),
    )
    assert np.array_equal(
        full["short_signal"].iloc[:overlap].to_numpy(),
        truncated["short_signal"].to_numpy(),
    )
