"""MACD trend + signal cross + histogram flip (causal, vectorized)."""

from __future__ import annotations

import numpy as np
import pandas as pd

from tradesim import Signal

STRATEGY_ID = "tsm_macd_trend"
STRATEGY_VERSION = "0.1.0"


def ema(x, n):
    return pd.Series(x).ewm(span=n, adjust=False).mean()


def build_signal_frame(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy().reset_index(drop=True)
    c = out["close"].to_numpy(float)
    h = out["high"].to_numpy(float)
    l = out["low"].to_numpy(float)
    macd = (ema(c, 12) - ema(c, 26)).to_numpy(float)
    signal = pd.Series(macd).ewm(span=9, adjust=False).mean().to_numpy(float)
    hist = macd - signal
    cross_up = (macd > signal) & (np.roll(macd, 1) <= np.roll(signal, 1))
    cross_dn = (macd < signal) & (np.roll(macd, 1) >= np.roll(signal, 1))
    hist_up = (hist > 0) & (np.roll(hist, 1) <= 0)
    hist_dn = (hist < 0) & (np.roll(hist, 1) >= 0)
    cross_up[0] = cross_dn[0] = hist_up[0] = hist_dn[0] = False
    long_sig = (macd > 0) & cross_up & hist_up
    short_sig = (macd < 0) & cross_dn & hist_dn
    long_sig[:40] = short_sig[:40] = False
    swing_lo = pd.Series(l).rolling(10, min_periods=10).min().shift(1).to_numpy(float)
    swing_hi = pd.Series(h).rolling(10, min_periods=10).max().shift(1).to_numpy(float)
    stop = np.full(len(out), np.nan)
    target = np.full(len(out), np.nan)
    stop[long_sig] = swing_lo[long_sig] * (1 - 1e-4)
    risk = np.maximum(c[long_sig] - stop[long_sig], c[long_sig] * 1e-4)
    target[long_sig] = c[long_sig] + 2.0 * risk
    stop[short_sig] = swing_hi[short_sig] * (1 + 1e-4)
    risk_s = np.maximum(stop[short_sig] - c[short_sig], c[short_sig] * 1e-4)
    target[short_sig] = c[short_sig] - 2.0 * risk_s
    out["macd"] = macd
    out["macd_signal"] = signal
    out["macd_hist"] = hist
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
                    tag="tsm_macd",
                )
            )
    return sigs
