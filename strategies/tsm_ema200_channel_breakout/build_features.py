from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from strategies.tsm_ema200_channel_breakout.signals import build_signal_frame


def build_features(ohlcv: pd.DataFrame, *, interval: str = "15m") -> pd.DataFrame:
    del interval
    feat = build_signal_frame(ohlcv.sort_values("ts_ms").reset_index(drop=True))
    # Leakage audit wants engineered columns only — drop raw warehouse passthroughs
    # and trade-management fields (stop/target near-identify labels).
    keep = [
        "ts_ms",
        "open",
        "high",
        "low",
        "close",
        "ema200_high",
        "ema200_low",
        "long_signal",
        "short_signal",
    ]
    cols = [c for c in keep if c in feat.columns]
    return feat[cols].copy()
