"""Premium / Discount mapping on swing legs (50% and Gann quarters)."""
from __future__ import annotations

import numpy as np
import pandas as pd


def premium_discount_from_swings(
    close: np.ndarray,
    last_swing_high: np.ndarray,
    last_swing_low: np.ndarray,
) -> pd.DataFrame:
    """Map price into discount (<50%), equilibrium, premium (>50%) of current swing range."""
    rng = last_swing_high - last_swing_low
    valid = (~np.isnan(last_swing_high)) & (~np.isnan(last_swing_low)) & (rng > 0)
    pos = np.full(len(close), np.nan)
    pos[valid] = (close[valid] - last_swing_low[valid]) / rng[valid]

    discount = valid & (pos < 0.5)
    premium = valid & (pos > 0.5)
    deep_discount = valid & (pos <= 0.25)
    deep_premium = valid & (pos >= 0.75)
    equilibrium = valid & (pos >= 0.45) & (pos <= 0.55)

    q25 = np.where(valid, last_swing_low + 0.25 * rng, np.nan)
    q50 = np.where(valid, last_swing_low + 0.50 * rng, np.nan)
    q75 = np.where(valid, last_swing_low + 0.75 * rng, np.nan)

    return pd.DataFrame(
        {
            "pd_position": pos,
            "in_discount": discount,
            "in_premium": premium,
            "deep_discount": deep_discount,
            "deep_premium": deep_premium,
            "at_equilibrium": equilibrium,
            "pd_q25": q25,
            "pd_q50": q50,
            "pd_q75": q75,
        }
    )


def fib_confluence_zone(
    last_swing_high: np.ndarray,
    last_swing_low: np.ndarray,
    fvg_top: np.ndarray,
    fvg_bot: np.ndarray,
    golden_lo: float = 0.50,
    golden_hi: float = 0.618,
) -> np.ndarray:
    """True when active FVG overlaps Fib golden pocket of the swing."""
    rng = last_swing_high - last_swing_low
    valid = (~np.isnan(rng)) & (rng > 0) & (~np.isnan(fvg_top)) & (~np.isnan(fvg_bot))
    fib_lo = last_swing_low + golden_lo * rng
    fib_hi = last_swing_low + golden_hi * rng
    # Overlap of [fvg_bot, fvg_top] with [fib_lo, fib_hi]
    overlap = valid & (np.minimum(fvg_top, fib_hi) >= np.maximum(fvg_bot, fib_lo))
    return overlap


def compute_premium_discount(
    df: pd.DataFrame,
    last_swing_high: np.ndarray,
    last_swing_low: np.ndarray,
    fvg_top: np.ndarray | None = None,
    fvg_bot: np.ndarray | None = None,
) -> pd.DataFrame:
    out = premium_discount_from_swings(
        df["close"].to_numpy(float), last_swing_high, last_swing_low
    )
    if fvg_top is not None and fvg_bot is not None:
        out["fvg_fib_golden"] = fib_confluence_zone(
            last_swing_high, last_swing_low, fvg_top, fvg_bot
        )
    else:
        out["fvg_fib_golden"] = False
    return out
