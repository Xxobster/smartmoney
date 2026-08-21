"""Causal checks for the ADX regime feature frame."""

from __future__ import annotations

import numpy as np
import pandas as pd

from strategies.coinquant_regime_adx.signals import WARMUP, build_signal_frame


def _frame(n: int, seed: int = 2) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    close = 100 + np.cumsum(rng.normal(0, 0.6, n))
    return pd.DataFrame(
        {
            "ts_ms": np.arange(n, dtype=np.int64) * 3_600_000,
            "open": close,
            "high": close + 0.8,
            "low": close - 0.8,
            "close": close,
        }
    )


def test_no_signal_before_warmup():
    feat = build_signal_frame(_frame(WARMUP + 30))
    assert int(feat["long_signal"].iloc[:WARMUP].sum()) == 0
    assert int(feat["short_signal"].iloc[:WARMUP].sum()) == 0


def test_features_have_no_future_shift():
    df = _frame(WARMUP + 80)
    full = build_signal_frame(df)
    truncated = build_signal_frame(df.iloc[:-12].copy())
    overlap = len(truncated)
    assert np.array_equal(
        full["long_signal"].iloc[:overlap].to_numpy(),
        truncated["long_signal"].to_numpy(),
    )
    assert np.array_equal(
        full["short_signal"].iloc[:overlap].to_numpy(),
        truncated["short_signal"].to_numpy(),
    )
