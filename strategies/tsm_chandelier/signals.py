"""ATR-band breakout with Chandelier-style stop (causal, vectorized)."""

from __future__ import annotations

import numpy as np
import pandas as pd

from tradesim import Signal

STRATEGY_ID = "tsm_chandelier"
STRATEGY_VERSION = "0.1.0"


def ema(x, n):
    return pd.Series(x).ewm(span=n, adjust=False).mean().to_numpy(float)


def atr(h, l, c, n=14):
    prev = np.roll(c, 1)
    prev[0] = c[0]
    tr = np.maximum(h - l, np.maximum(np.abs(h - prev), np.abs(l - prev)))
    return pd.Series(tr).rolling(n, min_periods=n).mean().to_numpy(float)


def build_signal_frame(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy().reset_index(drop=True)
    h = out["high"].to_numpy(float)
    l = out["low"].to_numpy(float)
    c = out["close"].to_numpy(float)
    a = atr(h, l, c, 14)
    e50 = ema(c, 50)
    upper = c + 2.5 * a
    lower = c - 2.5 * a
    # use prior-bar bands for break (avoid using same-bar band with close)
    upper_p = np.roll(upper, 1)
    lower_p = np.roll(lower, 1)
    upper_p[0] = lower_p[0] = np.nan
    long_raw = (c > upper_p) & (c > e50) & np.isfinite(upper_p)
    short_raw = (c < lower_p) & (c < e50) & np.isfinite(lower_p)
    long_sig = long_raw & ~np.roll(long_raw, 1)
    short_sig = short_raw & ~np.roll(short_raw, 1)
    long_sig[0] = short_sig[0] = False
    long_sig[:55] = short_sig[:55] = False
    both = long_sig & short_sig
    long_sig[both] = short_sig[both] = False
    hh = pd.Series(h).rolling(22, min_periods=22).max().to_numpy(float)
    ll = pd.Series(l).rolling(22, min_periods=22).min().to_numpy(float)
    chand_long = hh - 3.0 * a
    chand_short = ll + 3.0 * a
    stop = np.full(len(out), np.nan)
    target = np.full(len(out), np.nan)
    # synthetic wide target; primary exit is chandelier stop / max_hold
    stop[long_sig] = chand_long[long_sig]
    risk = np.maximum(c[long_sig] - stop[long_sig], c[long_sig] * 1e-4)
    target[long_sig] = c[long_sig] + 3.0 * risk
    stop[short_sig] = chand_short[short_sig]
    risk_s = np.maximum(stop[short_sig] - c[short_sig], c[short_sig] * 1e-4)
    target[short_sig] = c[short_sig] - 3.0 * risk_s
    out["atr"] = a
    out["long_signal"] = long_sig
    out["short_signal"] = short_sig
    out["stop_price"] = stop
    out["target_price"] = target
    return out


def to_tradesim_signals(feat: pd.DataFrame, symbol: str, max_hold_bars: int = 48) -> list[Signal]:
    sigs = []
    ts = feat["ts_ms"].to_numpy(np.int64)
    for i in range(len(feat)):
        if bool(feat["long_signal"].iloc[i]) ^ bool(feat["short_signal"].iloc[i]):
            side = 1 if bool(feat["long_signal"].iloc[i]) else -1
            sp, tp = float(feat["stop_price"].iloc[i]), float(feat["target_price"].iloc[i])
            if np.isnan(sp) or np.isnan(tp):
                continue
            px = float(feat["close"].iloc[i])
            if side == 1 and not (sp < px < tp):
                continue
            if side == -1 and not (tp < px < sp):
                continue
            sigs.append(
                Signal(
                    ts_ms=int(ts[i]),
                    side=side,
                    symbol=symbol,
                    stop_price=sp,
                    target_price=tp,
                    max_hold_bars=max_hold_bars,
                    tag="tsm_chand",
                )
            )
    return sigs
