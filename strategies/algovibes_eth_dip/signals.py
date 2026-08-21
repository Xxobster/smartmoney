"""Hourly dip-buy: return <= -1%, +0.5% target or 5-bar hold. Vectorized."""

from __future__ import annotations

import numpy as np
import pandas as pd

from tradesim import Signal

STRATEGY_ID = "algovibes_eth_dip"
STRATEGY_VERSION = "0.1.0"

DROP = 0.01
RISE = 0.005
PROT_STOP = 0.03  # OUR INTERPRETATION


def build_signal_frame(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy().reset_index(drop=True)
    c = out["close"].to_numpy(float)
    prev = np.roll(c, 1)
    prev[0] = np.nan
    ret = (c / prev) - 1.0
    long_sig = ret <= -DROP
    long_sig[0] = False
    long_sig[:2] = False
    stop = np.full(len(out), np.nan)
    target = np.full(len(out), np.nan)
    stop[long_sig] = c[long_sig] * (1.0 - PROT_STOP)
    target[long_sig] = c[long_sig] * (1.0 + RISE)
    out["hourly_return"] = ret
    out["long_signal"] = long_sig
    out["short_signal"] = False
    out["stop_price"] = stop
    out["target_price"] = target
    return out


def to_tradesim_signals(feat: pd.DataFrame, symbol: str, max_hold_bars: int = 5) -> list[Signal]:
    sigs: list[Signal] = []
    ts = feat["ts_ms"].to_numpy(np.int64)
    long_sig = feat["long_signal"].to_numpy(bool)
    stop = feat["stop_price"].to_numpy(float)
    target = feat["target_price"].to_numpy(float)
    px = feat["close"].to_numpy(float)
    for i in range(len(feat)):
        if not long_sig[i]:
            continue
        sp, tp, p = float(stop[i]), float(target[i]), float(px[i])
        if not (sp < p < tp):
            continue
        sigs.append(
            Signal(
                ts_ms=int(ts[i]),
                side=1,
                symbol=symbol,
                stop_price=sp,
                target_price=tp,
                max_hold_bars=max_hold_bars,
                tag="algovibes_dip",
            )
        )
    return sigs
