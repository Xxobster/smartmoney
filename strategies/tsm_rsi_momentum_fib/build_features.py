"""Leakage builder for tsm_rsi_momentum_fib."""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from strategies.tsm_rsi_momentum_fib.signals import build_signal_frame


def build_features(ohlcv: pd.DataFrame, *, interval: str = "15m") -> pd.DataFrame:
    del interval
    df = ohlcv.copy().sort_values("ts_ms").reset_index(drop=True)
    feat = build_signal_frame(df)
    # Stop/target are trade management fields derived from the signal bar close;
    # exclude from leakage feature matrix (they near-identify labels by construction).
    return feat.drop(columns=["stop_price", "target_price"], errors="ignore")
