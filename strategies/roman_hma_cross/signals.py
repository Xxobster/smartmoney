"""Hull Moving Average (HMA) close-cross H0 — vectorized; sides via side_mode.

Fair default: HMA length 16 (Alan Hull), not the creator heatmap.
Video exit is close below HMA; tradesim has no dynamic HMA trail, so H0 uses
a causal stop at the HMA on the signal bar plus a safety max_hold.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from strategies.common.signal_sides import SideMode
from strategies.common.wma import hull_moving_average
from tradesim import Signal

STRATEGY_ID = "roman_hma_cross"
STRATEGY_VERSION = "0.1.0"

HMA_N = 16
WARMUP = HMA_N + 8


def build_signal_frame(df: pd.DataFrame) -> pd.DataFrame:
    out = df.sort_values("ts_ms").reset_index(drop=True).copy()
    c = out["close"].to_numpy(float)
    hma = hull_moving_average(c, HMA_N)
    prev_c = np.roll(c, 1)
    prev_h = np.roll(hma, 1)
    prev_c[0] = prev_h[0] = np.nan
    long_raw = (c > hma) & (prev_c <= prev_h)
    short_raw = (c < hma) & (prev_c >= prev_h)
    long_raw[:WARMUP] = False
    short_raw[:WARMUP] = False
    both = long_raw & short_raw
    long_raw[both] = short_raw[both] = False
    stop = np.full(len(out), np.nan)
    stop[long_raw] = hma[long_raw]
    stop[short_raw] = hma[short_raw]
    out["hma16"] = hma
    out["long_signal"] = long_raw
    out["short_signal"] = short_raw
    out["stop_price"] = stop
    out["target_price"] = np.nan
    return out


def to_tradesim_signals(
    feat: pd.DataFrame,
    symbol: str,
    max_hold_bars: int = 96,
    *,
    side_mode: SideMode = "long",
) -> list[Signal]:
    sigs: list[Signal] = []
    ts = feat["ts_ms"].to_numpy(np.int64)
    long_sig = feat["long_signal"].to_numpy(bool)
    short_sig = feat["short_signal"].to_numpy(bool)
    stop = feat["stop_price"].to_numpy(float)
    px = feat["close"].to_numpy(float)
    use_long = side_mode in ("long", "long_mirror")
    use_short = side_mode in ("short", "short_mirror")
    for i in range(len(feat)):
        p = float(px[i])
        sp = float(stop[i])
        if use_long and long_sig[i]:
            if not np.isfinite(sp) or not (sp < p):
                continue
            sigs.append(
                Signal(
                    ts_ms=int(ts[i]),
                    side=1,
                    symbol=symbol,
                    stop_price=sp,
                    target_price=None,
                    max_hold_bars=max_hold_bars,
                    tag="hma_long" if side_mode == "long" else "hma_long_mirror",
                )
            )
        elif use_short and short_sig[i]:
            if not np.isfinite(sp) or not (sp > p):
                continue
            sigs.append(
                Signal(
                    ts_ms=int(ts[i]),
                    side=-1,
                    symbol=symbol,
                    stop_price=sp,
                    target_price=None,
                    max_hold_bars=max_hold_bars,
                    tag="hma_short_mirror" if side_mode == "short_mirror" else "hma_short",
                )
            )
    return sigs
