"""Liquidity pools, equal highs/lows, and sweep detection."""
from __future__ import annotations

import numpy as np
import pandas as pd


def equal_extremes(
    levels: np.ndarray,
    mask: np.ndarray,
    tol_frac: float = 0.0005,
) -> np.ndarray:
    """Mark bars whose swing level approximately equals a prior swing level."""
    n = len(levels)
    eq = np.zeros(n, dtype=bool)
    idxs = np.where(mask)[0]
    if len(idxs) < 2:
        return eq
    vals = levels[idxs]
    # Compare each swing to previous swing within relative tolerance
    prev = vals[:-1]
    cur = vals[1:]
    close = np.abs(cur - prev) <= (np.maximum(np.abs(cur), 1e-12) * tol_frac)
    eq[idxs[1:][close]] = True
    return eq


def liquidity_sweeps(
    high: np.ndarray,
    low: np.ndarray,
    close: np.ndarray,
    open_: np.ndarray,
    last_swing_high: np.ndarray,
    last_swing_low: np.ndarray,
) -> pd.DataFrame:
    """Detect stop-run sweeps: pierce beyond swing then close back inside."""
    n = len(close)
    bull_sweep = np.zeros(n, dtype=bool)  # sweep lows (sellside) then reclaim
    bear_sweep = np.zeros(n, dtype=bool)  # sweep highs (buyside) then reject

    valid_sl = ~np.isnan(last_swing_low)
    valid_sh = ~np.isnan(last_swing_high)

    # Bullish sweep: low < last swing low, close > last swing low
    bull_sweep[valid_sl] = (low[valid_sl] < last_swing_low[valid_sl]) & (
        close[valid_sl] > last_swing_low[valid_sl]
    )
    # Bearish sweep: high > last swing high, close < last swing high
    bear_sweep[valid_sh] = (high[valid_sh] > last_swing_high[valid_sh]) & (
        close[valid_sh] < last_swing_high[valid_sh]
    )

    sweep_extreme = np.where(bull_sweep, low, np.where(bear_sweep, high, np.nan))
    return pd.DataFrame(
        {
            "bull_sweep": bull_sweep,
            "bear_sweep": bear_sweep,
            "sweep_extreme": sweep_extreme,
        }
    )


def session_high_low(
    ts_ms: np.ndarray,
    high: np.ndarray,
    low: np.ndarray,
    session: str = "asia",
) -> tuple[np.ndarray, np.ndarray]:
    """Approximate session high/low (UTC hours). Asia 00-08, London 07-16, NY 12-21."""
    hours = ((ts_ms // 3_600_000) % 24).astype(int)
    if session == "asia":
        in_sess = (hours >= 0) & (hours < 8)
    elif session == "london":
        in_sess = (hours >= 7) & (hours < 16)
    else:  # ny
        in_sess = (hours >= 12) & (hours < 21)

    n = len(high)
    sess_h = np.full(n, np.nan)
    sess_l = np.full(n, np.nan)
    # Daily session reset at UTC midnight
    day = ts_ms // 86_400_000
    # Vectorized groupby via pandas
    df = pd.DataFrame({"day": day, "in": in_sess, "high": high, "low": low})
    # Expanding max within session for each day is path dependent; use transform after filter
    # Simpler causal approach: cumulative max/min within (day, session) then ffill
    g = df.copy()
    g.loc[~g["in"], ["high", "low"]] = np.nan
    g["sess_h"] = g.groupby("day")["high"].cummax()
    g["sess_l"] = g.groupby("day")["low"].cummin()
    g["sess_h"] = g["sess_h"].ffill()
    g["sess_l"] = g["sess_l"].ffill()
    return g["sess_h"].to_numpy(), g["sess_l"].to_numpy()


def previous_day_high_low(
    ts_ms: np.ndarray,
    high: np.ndarray,
    low: np.ndarray,
) -> tuple[np.ndarray, np.ndarray]:
    day = ts_ms // 86_400_000
    df = pd.DataFrame({"day": day, "high": high, "low": low})
    daily = df.groupby("day", as_index=False).agg(day_high=("high", "max"), day_low=("low", "min"))
    daily["pdh"] = daily["day_high"].shift(1)
    daily["pdl"] = daily["day_low"].shift(1)
    merged = df.merge(daily[["day", "pdh", "pdl"]], on="day", how="left")
    return merged["pdh"].to_numpy(), merged["pdl"].to_numpy()


def round_number_proximity(price: np.ndarray, step: float = 1000.0) -> np.ndarray:
    """Distance to nearest round number as fraction of price."""
    nearest = np.round(price / step) * step
    return np.abs(price - nearest) / np.maximum(np.abs(price), 1e-12)


def compute_liquidity(
    df: pd.DataFrame,
    swing_high: np.ndarray,
    swing_low: np.ndarray,
    last_swing_high: np.ndarray,
    last_swing_low: np.ndarray,
) -> pd.DataFrame:
    high = df["high"].to_numpy(dtype=float)
    low = df["low"].to_numpy(dtype=float)
    close = df["close"].to_numpy(dtype=float)
    open_ = df["open"].to_numpy(dtype=float)
    ts = df["ts_ms"].to_numpy(dtype=np.int64)

    sweeps = liquidity_sweeps(high, low, close, open_, last_swing_high, last_swing_low)
    eq_h = equal_extremes(high, swing_high)
    eq_l = equal_extremes(low, swing_low)
    pdh, pdl = previous_day_high_low(ts, high, low)
    asia_h, asia_l = session_high_low(ts, high, low, "asia")

    out = sweeps.copy()
    out["equal_high"] = eq_h
    out["equal_low"] = eq_l
    out["pdh"] = pdh
    out["pdl"] = pdl
    out["asia_high"] = asia_h
    out["asia_low"] = asia_l
    out["round_prox"] = round_number_proximity(close)
    return out
