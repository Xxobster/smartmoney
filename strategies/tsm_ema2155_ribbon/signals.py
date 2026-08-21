"""21/55 EMA ribbon pullback reclaim (causal, vectorized)."""

from __future__ import annotations

import numpy as np
import pandas as pd

from tradesim import Signal

STRATEGY_ID = "tsm_ema2155_ribbon"
STRATEGY_VERSION = "0.1.0"


def ema(x, n):
    return pd.Series(x).ewm(span=n, adjust=False).mean().to_numpy(float)


def build_signal_frame(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy().reset_index(drop=True)
    h = out["high"].to_numpy(float)
    l = out["low"].to_numpy(float)
    c = out["close"].to_numpy(float)
    e21 = ema(c, 21)
    e55 = ema(c, 55)
    e55_up = e55 > np.roll(e55, 1)
    e55_dn = e55 < np.roll(e55, 1)
    e55_up[0] = e55_dn[0] = False
    ribbon_hi = np.maximum(e21, e55)
    ribbon_lo = np.minimum(e21, e55)
    touch_ribbon = (l <= ribbon_hi) & (h >= ribbon_lo)
    long_raw = e55_up & (e21 > e55) & touch_ribbon & (c > e21) & (np.roll(c, 1) <= np.roll(e21, 1))
    short_raw = e55_dn & (e21 < e55) & touch_ribbon & (c < e21) & (np.roll(c, 1) >= np.roll(e21, 1))
    long_raw[0] = short_raw[0] = False
    long_sig = long_raw & ~np.roll(long_raw, 1)
    short_sig = short_raw & ~np.roll(short_raw, 1)
    long_sig[0] = short_sig[0] = False
    long_sig[:60] = short_sig[:60] = False
    both = long_sig & short_sig
    long_sig[both] = short_sig[both] = False

    stop = np.full(len(out), np.nan)
    target = np.full(len(out), np.nan)
    stop[long_sig] = np.minimum(l[long_sig], ribbon_lo[long_sig]) * (1 - 1e-4)
    risk = np.maximum(c[long_sig] - stop[long_sig], c[long_sig] * 1e-4)
    target[long_sig] = c[long_sig] + 2.0 * risk
    stop[short_sig] = np.maximum(h[short_sig], ribbon_hi[short_sig]) * (1 + 1e-4)
    risk_s = np.maximum(stop[short_sig] - c[short_sig], c[short_sig] * 1e-4)
    target[short_sig] = c[short_sig] - 2.0 * risk_s

    out["ema21"] = e21
    out["ema55"] = e55
    out["long_signal"] = long_sig
    out["short_signal"] = short_sig
    out["stop_price"] = stop
    out["target_price"] = target
    return out


def to_tradesim_signals(feat: pd.DataFrame, symbol: str, max_hold_bars: int = 36) -> list[Signal]:
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
                    tag="tsm_ribbon",
                )
            )
    return sigs
