"""EMA20/EMA200 trend alignment entries (causal, vectorized)."""

from __future__ import annotations

import numpy as np
import pandas as pd

from tradesim import Signal

STRATEGY_ID = "tsm_ema20_200"
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
    e20 = ema(c, 20)
    e200 = ema(c, 200)
    a = atr(h, l, c, 14)
    e20_up = e20 > np.roll(e20, 1)
    e20_dn = e20 < np.roll(e20, 1)
    e20_up[0] = e20_dn[0] = False
    long_raw = (c > e20) & (e20 > e200) & e20_up & np.isfinite(a)
    short_raw = (c < e20) & (e20 < e200) & e20_dn & np.isfinite(a)
    long_sig = long_raw & ~np.roll(long_raw, 1)
    short_sig = short_raw & ~np.roll(short_raw, 1)
    long_sig[0] = short_sig[0] = False
    long_sig[:210] = short_sig[:210] = False
    both = long_sig & short_sig
    long_sig[both] = short_sig[both] = False

    stop = np.full(len(out), np.nan)
    target = np.full(len(out), np.nan)
    stop[long_sig] = c[long_sig] - 1.5 * a[long_sig]
    risk = np.maximum(c[long_sig] - stop[long_sig], c[long_sig] * 1e-4)
    target[long_sig] = c[long_sig] + 2.0 * risk
    stop[short_sig] = c[short_sig] + 1.5 * a[short_sig]
    risk_s = np.maximum(stop[short_sig] - c[short_sig], c[short_sig] * 1e-4)
    target[short_sig] = c[short_sig] - 2.0 * risk_s

    out["ema20"] = e20
    out["ema200"] = e200
    out["long_signal"] = long_sig
    out["short_signal"] = short_sig
    out["stop_price"] = stop
    out["target_price"] = target
    return out


def to_tradesim_signals(feat: pd.DataFrame, symbol: str, max_hold_bars: int = 40) -> list[Signal]:
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
                    tag="tsm_ema20_200",
                )
            )
    return sigs
