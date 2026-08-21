"""Unit tests for SMC primitives and causality guards."""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from engine.parity_tests import (
    future_mutation_test,
    swing_confirmation_causal,
    truncation_invariance_test,
)
from smc.confluence import ConfluenceConfig, build_feature_frame, score_confluence
from smc.fvg import detect_fvg
from smc.structure import swing_highs_lows_vectorized


def _synth_ohlcv(n: int = 200, seed: int = 0) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    ts0 = 1_600_000_000_000
    step = 900_000
    close = 100 + np.cumsum(rng.normal(0, 0.5, n))
    open_ = np.roll(close, 1)
    open_[0] = close[0]
    high = np.maximum(open_, close) + rng.uniform(0, 0.4, n)
    low = np.minimum(open_, close) - rng.uniform(0, 0.4, n)
    vol = rng.uniform(10, 100, n)
    return pd.DataFrame(
        {
            "source": "binance",
            "symbol": "BTCUSDT",
            "timeframe": "15m",
            "ts_ms": ts0 + np.arange(n) * step,
            "open": open_,
            "high": high,
            "low": low,
            "close": close,
            "volume": vol,
            "price_type": "last",
            "is_complete": 1,
        }
    )


def test_swing_confirmation_causal_prefix():
    df = _synth_ohlcv()
    sh, sl, pivot_h, pivot_l = swing_highs_lows_vectorized(
        df["high"].to_numpy(), df["low"].to_numpy(), 3, 3
    )
    assert sh.shape == pivot_h.shape
    # No confirmations before left+right
    assert not sh[:6].any()
    assert not sl[:6].any()
    # Pivot prices only on confirm bars
    assert np.isnan(pivot_h[~sh]).all()
    assert np.isnan(pivot_l[~sl]).all()
    assert swing_confirmation_causal(df["high"].to_numpy(), df["low"].to_numpy(), 3)


def test_bullish_fvg_wick():
    # Construct explicit 3-candle bullish wick FVG
    high = np.array([10.0, 12.0, 15.0])
    low = np.array([8.0, 11.0, 13.0])  # c1 high 10 < c3 low 13
    open_ = np.array([9.0, 11.0, 13.5])
    close = np.array([9.5, 11.5, 14.0])
    fvg = detect_fvg(high, low, open_, close, model="wick")
    # Known only after candle 3 closes → flag on index 2
    assert not bool(fvg.loc[1, "bull_fvg"])
    assert bool(fvg.loc[2, "bull_fvg"])


def test_feature_frame_and_signals():
    df = _synth_ohlcv(300)
    cfg = ConfluenceConfig(min_confluence_count=2, require_order_block=False)
    feat = build_feature_frame(df, cfg)
    scored = score_confluence(feat, cfg)
    assert len(feat) == len(df)
    assert "long_signal" in scored.columns
    assert "short_signal" in scored.columns


def test_future_mutation_pass():
    df = _synth_ohlcv(150)
    assert future_mutation_test(df)


def test_truncation_invariance():
    df = _synth_ohlcv(120)
    assert truncation_invariance_test(df)


def test_session_mask_killzones():
    from smc.confluence import session_mask

    # 2024-01-02 08:00 UTC -> hour 8 (London killzone)
    # 2024-01-02 13:00 UTC -> hour 13 (NY killzone)
    # 2024-01-02 03:00 UTC -> hour 3 (Asia, off)
    ts = np.array(
        [
            1704182400000,  # 2024-01-02 08:00:00 UTC
            1704200400000,  # 2024-01-02 13:00:00 UTC
            1704164400000,  # 2024-01-02 03:00:00 UTC
        ],
        dtype=np.int64,
    )
    m = session_mask(ts, "killzones")
    assert bool(m[0]) and bool(m[1]) and not bool(m[2])


def test_strategy_spec_session_fields():
    from llm.schema import StrategySpec

    s = StrategySpec(name="t", session_mode="killzones", confirm_bars=1)
    cfg = s.to_confluence_config()
    assert cfg.session_mode == "killzones"
    assert cfg.confirm_bars == 1
