"""Default Bollinger Band close above upper band + SMA 200. Vectorized."""

from __future__ import annotations

import numpy as np
import pandas as pd

from tradesim import Signal

STRATEGY_ID = "tradingrush_bb_breakout"
STRATEGY_VERSION = "0.1.0"

BB_PERIOD = 20
BB_K = 2.0
SMA_SLOW = 200
REWARD_R = 1.5
WARMUP = SMA_SLOW


def build_signal_frame(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy().reset_index(drop=True)
    c = out["close"].to_numpy(float)
    low = out["low"].to_numpy(float)
    mid = pd.Series(c).rolling(BB_PERIOD, min_periods=BB_PERIOD).mean().to_numpy(float)
    std = pd.Series(c).rolling(BB_PERIOD, min_periods=BB_PERIOD).std(ddof=0).to_numpy(float)
    upper = mid + BB_K * std
    sma200 = pd.Series(c).rolling(SMA_SLOW, min_periods=SMA_SLOW).mean().to_numpy(float)
    above_upper = c > upper
    prev_above = np.roll(above_upper, 1)
    prev_above[0] = False
    long_sig = above_upper & ~prev_above & (c > sma200)
    long_sig[:WARMUP] = False
    stop = np.full(len(out), np.nan)
    target = np.full(len(out), np.nan)
    ok = long_sig & np.isfinite(c) & np.isfinite(low)
    stop[ok] = low[ok]
    risk = np.maximum(c[ok] - stop[ok], c[ok] * 1e-4)
    target[ok] = c[ok] + REWARD_R * risk
    out["bb_mid"] = mid
    out["bb_upper"] = upper
    out["sma200"] = sma200
    out["long_signal"] = long_sig
    out["short_signal"] = False
    out["stop_price"] = stop
    out["target_price"] = target
    return out


def to_tradesim_signals(feat: pd.DataFrame, symbol: str, max_hold_bars: int = 96) -> list[Signal]:
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
                tag="tr_bb_break",
            )
        )
    return sigs
