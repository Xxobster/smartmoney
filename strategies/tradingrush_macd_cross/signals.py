"""Default MACD cross above signal below zero + SMA 200. Vectorized."""

from __future__ import annotations

import numpy as np
import pandas as pd

from tradesim import Signal

STRATEGY_ID = "tradingrush_macd_cross"
STRATEGY_VERSION = "0.1.0"

FAST = 12
SLOW = 26
SIGNAL_N = 9
SMA_SLOW = 200
REWARD_R = 1.5
WARMUP = SMA_SLOW


def build_signal_frame(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy().reset_index(drop=True)
    c = out["close"].to_numpy(float)
    low = out["low"].to_numpy(float)
    px = pd.Series(c)
    macd = px.ewm(span=FAST, adjust=False).mean() - px.ewm(span=SLOW, adjust=False).mean()
    sig = macd.ewm(span=SIGNAL_N, adjust=False).mean()
    macd_a = macd.to_numpy(float)
    sig_a = sig.to_numpy(float)
    prev_m = np.roll(macd_a, 1)
    prev_s = np.roll(sig_a, 1)
    prev_m[0] = prev_s[0] = np.nan
    cross_up = (macd_a > sig_a) & (prev_m <= prev_s)
    below_zero = (macd_a < 0.0) & (sig_a < 0.0)
    sma200 = px.rolling(SMA_SLOW, min_periods=SMA_SLOW).mean().to_numpy(float)
    long_sig = cross_up & below_zero & (c > sma200)
    long_sig[:WARMUP] = False
    stop = np.full(len(out), np.nan)
    target = np.full(len(out), np.nan)
    ok = long_sig & np.isfinite(c) & np.isfinite(low)
    stop[ok] = low[ok]
    risk = np.maximum(c[ok] - stop[ok], c[ok] * 1e-4)
    target[ok] = c[ok] + REWARD_R * risk
    out["macd"] = macd_a
    out["macd_signal"] = sig_a
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
                tag="tr_macd_x",
            )
        )
    return sigs
