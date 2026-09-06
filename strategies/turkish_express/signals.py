"""Turkish Express H0: MavilimW + Inverse Fisher + EMA 200 + 3R swing stop."""

from __future__ import annotations

import pandas as pd

from strategies.common.signal_sides import SideMode
from strategies.common.turkish_express import (
    WARMUP,
    build_turkish_signal_frame,
    to_turkish_tradesim_signals,
)
from tradesim import Signal

STRATEGY_ID = "turkish_express"
STRATEGY_VERSION = "0.1.0"

__all__ = ["STRATEGY_ID", "STRATEGY_VERSION", "WARMUP", "build_signal_frame", "to_tradesim_signals"]


def build_signal_frame(df: pd.DataFrame) -> pd.DataFrame:
    return build_turkish_signal_frame(df, trend="ema200")


def to_tradesim_signals(
    feat: pd.DataFrame,
    symbol: str,
    max_hold_bars: int = 48,
    *,
    side_mode: SideMode = "long",
) -> list[Signal]:
    return to_turkish_tradesim_signals(
        feat,
        symbol,
        max_hold_bars,
        side_mode=side_mode,
        tag_prefix="te",
    )
