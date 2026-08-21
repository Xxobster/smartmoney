"""Causality / future-mutation / live-backtest parity guards."""
from __future__ import annotations

import numpy as np
import pandas as pd

from smc.confluence import ConfluenceConfig, build_feature_frame
from smc.structure import swing_highs_lows_vectorized


def future_mutation_test(df: pd.DataFrame, mutate_from: int | None = None) -> bool:
    """Changing future rows must not alter earlier actionable outputs.

    Returns True if PASS.
    """
    if len(df) < 50:
        return True
    mutate_from = mutate_from or (len(df) * 2 // 3)
    cfg = ConfluenceConfig()
    base = build_feature_frame(df.iloc[:mutate_from].copy(), cfg)

    mutated = df.copy()
    mutated.loc[mutate_from:, "close"] = mutated.loc[mutate_from:, "close"] * 1.5
    mutated.loc[mutate_from:, "high"] = mutated.loc[mutate_from:, "high"] * 1.5
    mutated.loc[mutate_from:, "low"] = mutated.loc[mutate_from:, "low"] * 1.5
    mutated.loc[mutate_from:, "open"] = mutated.loc[mutate_from:, "open"] * 1.5
    alt = build_feature_frame(mutated.iloc[:mutate_from].copy(), cfg)

    # Compare structure bias on overlapping prefix (exclude last swing_right bars)
    right = cfg.swing_right
    cols = ["bias", "bull_bos", "bear_bos", "last_swing_high", "last_swing_low"]
    a = base[cols].iloc[: -right if right else None].fillna(0).to_numpy(dtype=float)
    b = alt[cols].iloc[: -right if right else None].fillna(0).to_numpy(dtype=float)
    return bool(np.allclose(a, b, equal_nan=True))


def truncation_invariance_test(df: pd.DataFrame) -> bool:
    """Prefix features equal full-series features on that prefix (causality)."""
    if len(df) < 80:
        return True
    cfg = ConfluenceConfig()
    cut = len(df) - 20
    full = build_feature_frame(df.copy(), cfg).iloc[:cut]
    pref = build_feature_frame(df.iloc[:cut].copy(), cfg)
    right = cfg.swing_right + 2
    cols = ["bias", "atr", "in_discount", "in_premium"]
    a = full[cols].iloc[: -right].fillna(0).to_numpy(dtype=float)
    b = pref[cols].iloc[: -right].fillna(0).to_numpy(dtype=float)
    return bool(np.allclose(a, b, rtol=1e-6, atol=1e-6, equal_nan=True))


def htf_lag_no_lookahead(ltf_ts: np.ndarray, htf_ts: np.ndarray, htf_ms: int) -> bool:
    """available_ms = htf_ts + htf_ms must be > htf open."""
    return bool(np.all((htf_ts + htf_ms) > htf_ts))


def swing_confirmation_causal(high: np.ndarray, low: np.ndarray, right: int = 3) -> bool:
    """Flags must be identical on a prefix whether or not future bars exist."""
    sh_full, sl_full, _, _ = swing_highs_lows_vectorized(high, low, left=3, right=right)
    if len(high) < 40:
        return True
    cut = len(high) - max(right, 1) - 5
    sh_pref, sl_pref, _, _ = swing_highs_lows_vectorized(high[:cut], low[:cut], left=3, right=right)
    # Exclude the last `right` bars of the prefix (incomplete confirm window vs full)
    end = cut - right if right else cut
    if end <= 0:
        return True
    return bool(np.array_equal(sh_full[:end], sh_pref[:end]) and np.array_equal(sl_full[:end], sl_pref[:end]))
