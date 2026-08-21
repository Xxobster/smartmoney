"""Market structure: swings, order flow, Break of Structure (BOS), Change of Character (CHOCH)."""
from __future__ import annotations

import numpy as np
import pandas as pd


def swing_highs_lows(
    high: np.ndarray,
    low: np.ndarray,
    left: int = 3,
    right: int = 3,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """Fractal swing highs/lows. Confirmed only after `right` bars (causal).

    Flags are True on the **confirmation** bar `i + right`, never on the pivot bar.
    Also returns pivot price series aligned to the confirmation bar (NaN elsewhere).
    """
    n = len(high)
    sh = np.zeros(n, dtype=bool)
    sl = np.zeros(n, dtype=bool)
    pivot_h = np.full(n, np.nan)
    pivot_l = np.full(n, np.nan)
    if n < left + right + 1:
        return sh, sl, pivot_h, pivot_l
    # At confirmation index j, pivot is i = j - right; window is [i-left, j] ⊆ past∪present.
    for j in range(left + right, n):
        i = j - right
        window_h = high[i - left : j + 1]
        window_l = low[i - left : j + 1]
        if high[i] >= window_h.max() and int(np.sum(window_h == high[i])) == 1:
            sh[j] = True
            pivot_h[j] = high[i]
        if low[i] <= window_l.min() and int(np.sum(window_l == low[i])) == 1:
            sl[j] = True
            pivot_l[j] = low[i]
    return sh, sl, pivot_h, pivot_l


def swing_highs_lows_vectorized(
    high: np.ndarray,
    low: np.ndarray,
    left: int = 3,
    right: int = 3,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """Causal swing detection via rolling windows ending at the confirmation bar."""
    n = len(high)
    sh = np.zeros(n, dtype=bool)
    sl = np.zeros(n, dtype=bool)
    pivot_h = np.full(n, np.nan)
    pivot_l = np.full(n, np.nan)
    if n < left + right + 1:
        return sh, sl, pivot_h, pivot_l
    s = pd.Series(high)
    lo = pd.Series(low)
    win = left + right + 1
    # roll_*[j] uses only bars [j-win+1, j] — no future peek
    roll_max = s.rolling(win, min_periods=win).max().to_numpy()
    roll_min = lo.rolling(win, min_periods=win).min().to_numpy()
    # uniqueness of pivot vs other bars in window (exclude pivot itself)
    # left side of pivot: rolling max of prior `left` bars at index i
    # right side of pivot: rolling max of bars (i+1..j) = last `right` bars ending at j
    left_max_at_i = s.shift(1).rolling(left, min_periods=left).max().to_numpy()
    left_min_at_i = lo.shift(1).rolling(left, min_periods=left).min().to_numpy()
    right_max_end_j = s.rolling(right, min_periods=right).max().to_numpy()
    right_min_end_j = lo.rolling(right, min_periods=right).min().to_numpy()

    j = np.arange(left + right, n)
    i = j - right
    piv_h = high[i]
    piv_l = low[i]
    # right window for confirmation is bars i+1..j which is exactly the rolling(right) at j
    ok_h = (
        (piv_h >= roll_max[j] - 1e-12)
        & (piv_h > left_max_at_i[i] + 1e-12)
        & (piv_h > right_max_end_j[j] + 1e-12)
    )
    ok_l = (
        (piv_l <= roll_min[j] + 1e-12)
        & (piv_l < left_min_at_i[i] - 1e-12)
        & (piv_l < right_min_end_j[j] - 1e-12)
    )
    sh[j[ok_h]] = True
    sl[j[ok_l]] = True
    pivot_h[j[ok_h]] = piv_h[ok_h]
    pivot_l[j[ok_l]] = piv_l[ok_l]
    return sh, sl, pivot_h, pivot_l


def last_swing_levels(
    pivot_h: np.ndarray,
    pivot_l: np.ndarray,
    sh: np.ndarray,
    sl: np.ndarray,
) -> tuple[np.ndarray, np.ndarray]:
    """Forward-fill last confirmed swing high/low **pivot price** (set on confirm bar)."""
    last_sh = np.full(len(pivot_h), np.nan)
    last_sl = np.full(len(pivot_l), np.nan)
    last_sh[sh] = pivot_h[sh]
    last_sl[sl] = pivot_l[sl]
    last_sh = pd.Series(last_sh).ffill().to_numpy()
    last_sl = pd.Series(last_sl).ffill().to_numpy()
    return last_sh, last_sl


def structure_events(
    close: np.ndarray,
    high: np.ndarray,
    low: np.ndarray,
    last_sh: np.ndarray,
    last_sl: np.ndarray,
    bos_requires_close: bool = True,
) -> pd.DataFrame:
    """Detect bullish/bearish BOS and CHOCH from swing levels.

    Simplified state machine using last major swing high/low:
    - Bullish BOS: close/high breaks last swing high while prior bias bullish-ish
    - Bearish BOS: close/low breaks last swing low
    - CHOCH: break against prior sequence of HH/HL or LH/LL
    """
    n = len(close)
    bull_bos = np.zeros(n, dtype=bool)
    bear_bos = np.zeros(n, dtype=bool)
    bull_choch = np.zeros(n, dtype=bool)
    bear_choch = np.zeros(n, dtype=bool)

    px_up = close if bos_requires_close else high
    px_dn = close if bos_requires_close else low

    # Bias from sequence of swing breaks
    bias = np.zeros(n, dtype=np.int8)  # 1 bull, -1 bear, 0 unk
    cur = 0
    for i in range(1, n):
        if not np.isnan(last_sh[i]) and px_up[i] > last_sh[i - 1] and last_sh[i - 1] == last_sh[i]:
            # break of swing high
            if cur == -1:
                bull_choch[i] = True
            else:
                bull_bos[i] = True
            cur = 1
        elif not np.isnan(last_sl[i]) and px_dn[i] < last_sl[i - 1] and last_sl[i - 1] == last_sl[i]:
            if cur == 1:
                bear_choch[i] = True
            else:
                bear_bos[i] = True
            cur = -1
        bias[i] = cur

    return pd.DataFrame(
        {
            "bias": bias,
            "bull_bos": bull_bos,
            "bear_bos": bear_bos,
            "bull_choch": bull_choch,
            "bear_choch": bear_choch,
            "last_swing_high": last_sh,
            "last_swing_low": last_sl,
        }
    )


def compute_structure(
    df: pd.DataFrame,
    left: int = 3,
    right: int = 3,
    bos_requires_close: bool = True,
) -> pd.DataFrame:
    """Full structure feature frame from OHLCV dataframe sorted by time."""
    high = df["high"].to_numpy(dtype=float)
    low = df["low"].to_numpy(dtype=float)
    close = df["close"].to_numpy(dtype=float)
    sh, sl, pivot_h, pivot_l = swing_highs_lows_vectorized(high, low, left, right)
    last_sh, last_sl = last_swing_levels(pivot_h, pivot_l, sh, sl)
    events = structure_events(close, high, low, last_sh, last_sl, bos_requires_close)
    out = events.copy()
    out["swing_high"] = sh
    out["swing_low"] = sl
    return out
