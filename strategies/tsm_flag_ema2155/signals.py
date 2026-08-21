"""Bull/bear flag breakout with EMA21/55 trend filter (causal, vectorized core)."""

from __future__ import annotations

import numpy as np
import pandas as pd

from tradesim import Signal

STRATEGY_ID = "tsm_flag_ema2155"
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
    e21 = ema(c, 21)
    e55 = ema(c, 55)
    a = atr(h, l, c, 14)
    n = len(out)
    long_sig = np.zeros(n, dtype=bool)
    short_sig = np.zeros(n, dtype=bool)
    stop = np.full(n, np.nan)
    target = np.full(n, np.nan)

    # Path-dependent flag scan — small fixed window loop (unavoidable structure detection).
    # Vectorized helpers above; only consolidation endpoints need sequential checks.
    min_flag, max_flag = 8, 30
    for i in range(80, n):
        if not np.isfinite(a[i]) or a[i] <= 0:
            continue
        uptrend = e21[i] > e55[i]
        downtrend = e21[i] < e55[i]
        for w in range(min_flag, max_flag + 1):
            j0 = i - w
            if j0 < 20:
                continue
            # pole: prior 20 bars before flag
            pole_hi = float(np.max(h[j0 - 20 : j0]))
            pole_lo = float(np.min(l[j0 - 20 : j0]))
            pole_h = pole_hi - pole_lo
            if pole_h < 1.5 * a[i]:
                continue
            flag_hi = float(np.max(h[j0:i]))
            flag_lo = float(np.min(l[j0:i]))
            flag_w = flag_hi - flag_lo
            if flag_w <= 0 or flag_w > 0.55 * pole_h:
                continue
            # mild counter-trend slope of midpoints
            mid0 = 0.5 * (h[j0] + l[j0])
            mid1 = 0.5 * (h[i - 1] + l[i - 1])
            if uptrend and mid1 > mid0:  # want slight downward/flat flag in uptrend
                continue
            if downtrend and mid1 < mid0:
                continue
            if uptrend and c[i] > flag_hi and c[i - 1] <= flag_hi:
                long_sig[i] = True
                stop[i] = flag_lo * (1 - 1e-4)
                risk = max(c[i] - stop[i], c[i] * 1e-4)
                target[i] = c[i] + 2.0 * risk
                break
            if downtrend and c[i] < flag_lo and c[i - 1] >= flag_lo:
                short_sig[i] = True
                stop[i] = flag_hi * (1 + 1e-4)
                risk = max(stop[i] - c[i], c[i] * 1e-4)
                target[i] = c[i] - 2.0 * risk
                break

    both = long_sig & short_sig
    long_sig[both] = short_sig[both] = False
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
                    tag="tsm_flag",
                )
            )
    return sigs
