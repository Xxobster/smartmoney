"""Impulse candle + volume at EMA50 / swing (causal)."""

from __future__ import annotations

import numpy as np
import pandas as pd

from tradesim import Signal

STRATEGY_ID = "tsm_impulse_volume"
STRATEGY_VERSION = "0.1.0"


def ema(x, n):
    return pd.Series(x).ewm(span=n, adjust=False).mean().to_numpy(float)


def build_signal_frame(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy().reset_index(drop=True)
    o = out["open"].to_numpy(float)
    h = out["high"].to_numpy(float)
    l = out["low"].to_numpy(float)
    c = out["close"].to_numpy(float)
    vol = out["volume"].to_numpy(float) if "volume" in out.columns else np.ones(len(out))
    e50 = ema(c, 50)
    vol_sma = pd.Series(vol).rolling(20, min_periods=20).mean().to_numpy(float)
    swing_hi = pd.Series(h).rolling(10, min_periods=10).max().shift(1).to_numpy(float)
    swing_lo = pd.Series(l).rolling(10, min_periods=10).min().shift(1).to_numpy(float)
    rng = np.maximum(h - l, 1e-12)
    body = np.abs(c - o)
    bull_imp = (c > o) & (c > np.roll(h, 1)) & (body / rng >= 0.60) & (vol > vol_sma)
    bear_imp = (c < o) & (c < np.roll(l, 1)) & (body / rng >= 0.60) & (vol > vol_sma)
    bull_imp[0] = bear_imp[0] = False
    near_sup = (l <= e50) | (l <= swing_lo * 1.002)
    near_res = (h >= e50) | (h >= swing_hi * 0.998)
    long_raw = (c > e50) & near_sup & bull_imp
    short_raw = (c < e50) & near_res & bear_imp
    long_sig = long_raw & ~np.roll(long_raw, 1)
    short_sig = short_raw & ~np.roll(short_raw, 1)
    long_sig[0] = short_sig[0] = False
    long_sig[:50] = short_sig[:50] = False

    stop = np.full(len(out), np.nan)
    target = np.full(len(out), np.nan)
    stop[long_sig] = l[long_sig] * (1 - 1e-4)
    risk = np.maximum(c[long_sig] - stop[long_sig], c[long_sig] * 1e-4)
    target[long_sig] = c[long_sig] + 2.0 * risk
    stop[short_sig] = h[short_sig] * (1 + 1e-4)
    risk_s = np.maximum(stop[short_sig] - c[short_sig], c[short_sig] * 1e-4)
    target[short_sig] = c[short_sig] - 2.0 * risk_s

    out["ema50"] = e50
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
                    tag="tsm_impulse",
                )
            )
    return sigs
