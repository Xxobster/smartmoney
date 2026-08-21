from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from strategies.tsm_flag_ema2155.signals import build_signal_frame


def build_features(ohlcv: pd.DataFrame, *, interval: str = "1h") -> pd.DataFrame:
    del interval
    feat = build_signal_frame(ohlcv.sort_values("ts_ms").reset_index(drop=True))
    keep = ["ts_ms", "open", "high", "low", "close", "ema21", "ema55", "long_signal", "short_signal"]
    return feat[[c for c in keep if c in feat.columns]].copy()
