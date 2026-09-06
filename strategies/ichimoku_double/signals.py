"""Double Ichimoku: lagged daily cloud/Tenkan-Kijun bias + 4-hour Chikou entry.

Pre-registered with the single-timeframe pack (not a search after seeing numbers).
"""

from __future__ import annotations

import pandas as pd

from strategies.common.ichimoku import (
    WARMUP_DOUBLE as WARMUP,
    build_ichimoku_signal_frame,
    to_ichimoku_tradesim_signals,
)
from strategies.common.signal_sides import SideMode
from tradesim import Signal

STRATEGY_ID = "ichimoku_double"
STRATEGY_VERSION = "0.1.0"


def build_signal_frame(df: pd.DataFrame) -> pd.DataFrame:
    return build_ichimoku_signal_frame(df, require_daily_bias=True)


def to_tradesim_signals(
    feat: pd.DataFrame,
    symbol: str,
    max_hold_bars: int = 48,
    *,
    side_mode: SideMode = "long",
) -> list[Signal]:
    return to_ichimoku_tradesim_signals(
        feat,
        symbol,
        max_hold_bars=max_hold_bars,
        side_mode=side_mode,
        tag_prefix="ichi2",
    )
