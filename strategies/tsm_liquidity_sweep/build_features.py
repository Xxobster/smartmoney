"""Leakage-audit feature builder for tsm_liquidity_sweep (single-TF OHLCV in → features out)."""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from smc.confluence import build_feature_frame, score_confluence
from strategies.tsm_liquidity_sweep.confluence_config import TSM_LIQUIDITY_H0


def build_features(ohlcv: pd.DataFrame, *, interval: str = "15m") -> pd.DataFrame:
    """Causal feature builder for packages/leakage.

    Expects columns: ts_ms, open, high, low, close[, volume].
    Computes SMC primitives + H0 confluence scores/signals on this frame only
    (no HTF join here — leakage audit is per builder frame).
    """
    del interval  # interface compatibility; bars already at the audited timeframe
    df = ohlcv.copy()
    if "ts_ms" not in df.columns:
        raise ValueError("ohlcv must include ts_ms")
    df = df.sort_values("ts_ms").reset_index(drop=True)
    feat = build_feature_frame(df, TSM_LIQUIDITY_H0)
    scored = score_confluence(feat, TSM_LIQUIDITY_H0)
    out = pd.concat([feat.reset_index(drop=True), scored.reset_index(drop=True)], axis=1)
    out = out.loc[:, ~out.columns.duplicated()]
    return out
