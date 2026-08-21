"""Volume Spread Analysis (VSA) confirmation helpers."""
from __future__ import annotations

import numpy as np
import pandas as pd


def atr(high: np.ndarray, low: np.ndarray, close: np.ndarray, n: int = 14) -> np.ndarray:
    prev_close = np.roll(close, 1)
    prev_close[0] = close[0]
    tr = np.maximum(high - low, np.maximum(np.abs(high - prev_close), np.abs(low - prev_close)))
    return pd.Series(tr).rolling(n, min_periods=1).mean().to_numpy()


def volume_confirm(
    volume: np.ndarray,
    lookback: int = 5,
    mult: float = 1.2,
) -> np.ndarray:
    """True when current volume > mult * mean of previous `lookback` bars (causal)."""
    vol = pd.Series(volume).fillna(0.0)
    prior_mean = vol.shift(1).rolling(lookback, min_periods=1).mean()
    return (vol > (mult * prior_mean)).fillna(False).to_numpy()


def effort_result(
    high: np.ndarray,
    low: np.ndarray,
    volume: np.ndarray,
    lookback: int = 20,
) -> pd.DataFrame:
    """Classify effort vs result: high vol + tiny range = absorption; high vol + big range = conviction."""
    rng = high - low
    vol = pd.Series(volume).fillna(0.0)
    rng_s = pd.Series(rng)
    vol_pctl = vol.rolling(lookback, min_periods=5).rank(pct=True)
    rng_pctl = rng_s.rolling(lookback, min_periods=5).rank(pct=True)
    conviction = (vol_pctl > 0.8) & (rng_pctl > 0.8)
    absorption = (vol_pctl > 0.8) & (rng_pctl < 0.3)
    weak_move = (vol_pctl < 0.3) & (rng_pctl > 0.8)
    return pd.DataFrame(
        {
            "vol_pctl": vol_pctl.to_numpy(),
            "range_pctl": rng_pctl.to_numpy(),
            "vsa_conviction": conviction.fillna(False).to_numpy(),
            "vsa_absorption": absorption.fillna(False).to_numpy(),
            "vsa_weak_move": weak_move.fillna(False).to_numpy(),
        }
    )


def compute_volume(
    df: pd.DataFrame,
    lookback: int = 5,
    mult: float = 1.2,
) -> pd.DataFrame:
    high = df["high"].to_numpy(float)
    low = df["low"].to_numpy(float)
    close = df["close"].to_numpy(float)
    volume = df["volume"].to_numpy(float) if "volume" in df.columns else np.zeros(len(df))
    out = effort_result(high, low, volume)
    out["volume_confirm"] = volume_confirm(volume, lookback, mult)
    out["atr"] = atr(high, low, close)
    return out
