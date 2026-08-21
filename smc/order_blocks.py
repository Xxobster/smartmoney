"""Order Blocks (OB) — last opposing candle before impulse."""
from __future__ import annotations

import numpy as np
import pandas as pd


def detect_order_blocks(
    open_: np.ndarray,
    high: np.ndarray,
    low: np.ndarray,
    close: np.ndarray,
    impulse_body_atr_mult: float = 1.0,
    atr: np.ndarray | None = None,
) -> pd.DataFrame:
    """Identify candidate bullish/bearish OBs.

    Bullish OB: last bearish candle before a bullish impulse (large green body).
    Bearish OB: last bullish candle before a bearish impulse.
    """
    n = len(close)
    body = close - open_
    bull_candle = body > 0
    bear_candle = body < 0
    abs_body = np.abs(body)

    if atr is None:
        # simple range proxy
        atr = pd.Series(high - low).rolling(14, min_periods=1).mean().to_numpy()

    impulse_up = bull_candle & (abs_body >= impulse_body_atr_mult * np.maximum(atr, 1e-12))
    impulse_dn = bear_candle & (abs_body >= impulse_body_atr_mult * np.maximum(atr, 1e-12))

    bull_ob = np.zeros(n, dtype=bool)
    bear_ob = np.zeros(n, dtype=bool)
    ob_top = np.full(n, np.nan)
    ob_bot = np.full(n, np.nan)
    ob_mid = np.full(n, np.nan)

    last_bear_idx = -1
    last_bull_idx = -1
    for i in range(n):
        if bear_candle[i]:
            last_bear_idx = i
        if bull_candle[i]:
            last_bull_idx = i
        # Attribute OB on the impulse bar (when the pattern is known), not on the
        # past opposing candle — writing onto j < i mutates history (leakage).
        if impulse_up[i] and last_bear_idx >= 0 and last_bear_idx < i:
            j = last_bear_idx
            bull_ob[i] = True
            ob_top[i] = high[j]
            ob_bot[i] = low[j]
            ob_mid[i] = 0.5 * (high[j] + low[j])
        if impulse_dn[i] and last_bull_idx >= 0 and last_bull_idx < i:
            j = last_bull_idx
            bear_ob[i] = True
            ob_top[i] = high[j]
            ob_bot[i] = low[j]
            ob_mid[i] = 0.5 * (high[j] + low[j])

    return pd.DataFrame(
        {
            "bull_ob": bull_ob,
            "bear_ob": bear_ob,
            "ob_top": ob_top,
            "ob_bot": ob_bot,
            "ob_mid": ob_mid,
            "impulse_up": impulse_up,
            "impulse_dn": impulse_dn,
        }
    )


def active_ob_zones(ob: pd.DataFrame, close: np.ndarray, max_age: int = 300) -> pd.DataFrame:
    n = len(close)
    bull_top = np.full(n, np.nan)
    bull_bot = np.full(n, np.nan)
    bear_top = np.full(n, np.nan)
    bear_bot = np.full(n, np.nan)
    bull_mid = np.full(n, np.nan)
    bear_mid = np.full(n, np.nan)

    bt = bb = bm = et = eb = em = np.nan
    age_b = age_e = 10**9
    tops = ob["ob_top"].to_numpy()
    bots = ob["ob_bot"].to_numpy()
    mids = ob["ob_mid"].to_numpy()
    bull = ob["bull_ob"].to_numpy()
    bear = ob["bear_ob"].to_numpy()

    for i in range(n):
        if bull[i]:
            bt, bb, bm, age_b = tops[i], bots[i], mids[i], 0
        if bear[i]:
            et, eb, em, age_e = tops[i], bots[i], mids[i], 0
        age_b += 1
        age_e += 1
        # Invalidation: close through opposite side of OB
        if not np.isnan(bb) and close[i] < bb:
            bt = bb = bm = np.nan
        if not np.isnan(et) and close[i] > et:
            et = eb = em = np.nan
        if age_b > max_age:
            bt = bb = bm = np.nan
        if age_e > max_age:
            et = eb = em = np.nan
        bull_top[i], bull_bot[i], bull_mid[i] = bt, bb, bm
        bear_top[i], bear_bot[i], bear_mid[i] = et, eb, em

    in_bull = (~np.isnan(bull_bot)) & (close >= bull_bot) & (close <= bull_top)
    in_bear = (~np.isnan(bear_bot)) & (close >= bear_bot) & (close <= bear_top)
    return pd.DataFrame(
        {
            "active_bull_ob_top": bull_top,
            "active_bull_ob_bot": bull_bot,
            "active_bull_ob_mid": bull_mid,
            "active_bear_ob_top": bear_top,
            "active_bear_ob_bot": bear_bot,
            "active_bear_ob_mid": bear_mid,
            "price_in_bull_ob": in_bull,
            "price_in_bear_ob": in_bear,
        }
    )


def compute_order_blocks(df: pd.DataFrame, atr: np.ndarray | None = None) -> pd.DataFrame:
    raw = detect_order_blocks(
        df["open"].to_numpy(float),
        df["high"].to_numpy(float),
        df["low"].to_numpy(float),
        df["close"].to_numpy(float),
        atr=atr,
    )
    zones = active_ob_zones(raw, df["close"].to_numpy(float))
    return pd.concat([raw, zones], axis=1)
