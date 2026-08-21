"""Fair Value Gaps (FVG) / imbalances — body or wick model."""
from __future__ import annotations

import numpy as np
import pandas as pd


def detect_fvg(
    high: np.ndarray,
    low: np.ndarray,
    open_: np.ndarray,
    close: np.ndarray,
    model: str = "wick",
) -> pd.DataFrame:
    """3-candle FVG detection.

    wick model (Module 5): bullish if candle1 high < candle3 low;
    body model (Module 4 wording): use bodies.
    Gap is attributed to the middle (impulse) candle index i=1 in [0,1,2] => index t.
    """
    n = len(close)
    bull = np.zeros(n, dtype=bool)
    bear = np.zeros(n, dtype=bool)
    top = np.full(n, np.nan)
    bot = np.full(n, np.nan)

    if n < 3:
        return pd.DataFrame(
            {"bull_fvg": bull, "bear_fvg": bear, "fvg_top": top, "fvg_bot": bot, "fvg_mid": top}
        )

    if model == "body":
        c1_hi = np.maximum(open_[:-2], close[:-2])
        c1_lo = np.minimum(open_[:-2], close[:-2])
        c3_hi = np.maximum(open_[2:], close[2:])
        c3_lo = np.minimum(open_[2:], close[2:])
    else:
        c1_hi = high[:-2]
        c1_lo = low[:-2]
        c3_hi = high[2:]
        c3_lo = low[2:]

    # Bullish gap: c1 high < c3 low
    b = c1_hi < c3_lo
    # Bearish gap: c1 low > c3 high
    e = c1_lo > c3_hi

    # Store on candle-3 index (first bar where the 3-candle pattern is fully known).
    # Tagging the middle impulse bar would look ahead one candle.
    idx = np.arange(2, n)
    bull[idx] = b
    bear[idx] = e
    top[idx] = np.where(b, c3_lo, np.where(e, c1_lo, np.nan))
    bot[idx] = np.where(b, c1_hi, np.where(e, c3_hi, np.nan))
    mid = (top + bot) / 2.0

    return pd.DataFrame(
        {
            "bull_fvg": bull,
            "bear_fvg": bear,
            "fvg_top": top,
            "fvg_bot": bot,
            "fvg_mid": mid,
        }
    )


def active_fvg_zones(
    fvg: pd.DataFrame,
    close: np.ndarray,
    max_age: int = 200,
) -> pd.DataFrame:
    """Track most recent unfilled bullish/bearish FVG zone (vectorized approximate)."""
    n = len(close)
    bull_top = np.full(n, np.nan)
    bull_bot = np.full(n, np.nan)
    bear_top = np.full(n, np.nan)
    bear_bot = np.full(n, np.nan)

    bt = bb = et = eb = np.nan
    age_b = age_e = 10**9
    tops = fvg["fvg_top"].to_numpy()
    bots = fvg["fvg_bot"].to_numpy()
    bull = fvg["bull_fvg"].to_numpy()
    bear = fvg["bear_fvg"].to_numpy()

    for i in range(n):
        if bull[i]:
            bt, bb, age_b = tops[i], bots[i], 0
        if bear[i]:
            et, eb, age_e = tops[i], bots[i], 0
        age_b += 1
        age_e += 1
        # Fill: price trades through zone
        if not np.isnan(bb) and close[i] < bb:
            bt = bb = np.nan
        if not np.isnan(et) and close[i] > et:
            et = eb = np.nan
        if age_b > max_age:
            bt = bb = np.nan
        if age_e > max_age:
            et = eb = np.nan
        bull_top[i], bull_bot[i] = bt, bb
        bear_top[i], bear_bot[i] = et, eb

    in_bull = (~np.isnan(bull_bot)) & (close >= bull_bot) & (close <= bull_top)
    in_bear = (~np.isnan(bear_bot)) & (close >= bear_bot) & (close <= bear_top)
    return pd.DataFrame(
        {
            "active_bull_fvg_top": bull_top,
            "active_bull_fvg_bot": bull_bot,
            "active_bear_fvg_top": bear_top,
            "active_bear_fvg_bot": bear_bot,
            "price_in_bull_fvg": in_bull,
            "price_in_bear_fvg": in_bear,
        }
    )


def compute_fvg(df: pd.DataFrame, model: str = "wick", max_age: int = 200) -> pd.DataFrame:
    raw = detect_fvg(
        df["high"].to_numpy(float),
        df["low"].to_numpy(float),
        df["open"].to_numpy(float),
        df["close"].to_numpy(float),
        model=model,
    )
    zones = active_fvg_zones(raw, df["close"].to_numpy(float), max_age=max_age)
    return pd.concat([raw, zones], axis=1)
