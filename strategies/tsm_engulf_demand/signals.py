"""Bullish engulfing at prior swing-low demand (causal, vectorized)."""

from __future__ import annotations

import numpy as np
import pandas as pd

from tradesim import Signal

STRATEGY_ID = "tsm_engulf_demand"
STRATEGY_VERSION = "0.1.0"


def build_signal_frame(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy().reset_index(drop=True)
    o = out["open"].to_numpy(float)
    h = out["high"].to_numpy(float)
    l = out["low"].to_numpy(float)
    c = out["close"].to_numpy(float)
    swing_lo = pd.Series(l).rolling(20, min_periods=20).min().shift(1).to_numpy(float)
    near_demand = np.isfinite(swing_lo) & (l <= swing_lo * 1.0015)
    prev_bear = np.roll(c, 1) < np.roll(o, 1)
    prev_bear[0] = False
    curr_bull = c > o
    engulfs = (c >= np.roll(o, 1)) & (o <= np.roll(c, 1)) & (np.abs(c - o) > np.abs(np.roll(c, 1) - np.roll(o, 1)))
    engulfs[0] = False
    long_raw = near_demand & prev_bear & curr_bull & engulfs
    long_sig = long_raw & ~np.roll(long_raw, 1)
    long_sig[0] = False
    long_sig[:25] = False
    short_sig = np.zeros(len(out), dtype=bool)

    stop = np.full(len(out), np.nan)
    target = np.full(len(out), np.nan)
    stop[long_sig] = l[long_sig] * (1 - 1e-4)
    risk = np.maximum(c[long_sig] - stop[long_sig], c[long_sig] * 1e-4)
    target[long_sig] = c[long_sig] + 2.0 * risk

    out["swing_lo"] = swing_lo
    out["long_signal"] = long_sig
    out["short_signal"] = short_sig
    out["stop_price"] = stop
    out["target_price"] = target
    return out


def to_tradesim_signals(feat: pd.DataFrame, symbol: str, max_hold_bars: int = 24) -> list[Signal]:
    sigs = []
    ts = feat["ts_ms"].to_numpy(np.int64)
    for i in range(len(feat)):
        if bool(feat["long_signal"].iloc[i]):
            sp, tp = float(feat["stop_price"].iloc[i]), float(feat["target_price"].iloc[i])
            if np.isnan(sp) or np.isnan(tp):
                continue
            px = float(feat["close"].iloc[i])
            if not (sp < px < tp):
                continue
            sigs.append(
                Signal(
                    ts_ms=int(ts[i]),
                    side=1,
                    symbol=symbol,
                    stop_price=sp,
                    target_price=tp,
                    max_hold_bars=max_hold_bars,
                    tag="tsm_engulf",
                )
            )
    return sigs
