"""Volume climax + narrow-range reversal (causal, vectorized)."""

from __future__ import annotations

import numpy as np
import pandas as pd

from tradesim import Signal

STRATEGY_ID = "tsm_vol_climax"
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
    o = out["open"].to_numpy(float)
    h = out["high"].to_numpy(float)
    l = out["low"].to_numpy(float)
    c = out["close"].to_numpy(float)
    vol = out["volume"].to_numpy(float) if "volume" in out.columns else np.ones(len(out))
    e50 = ema(c, 50)
    a = atr(h, l, c, 14)
    vol_sma = pd.Series(vol).rolling(20, min_periods=20).mean().to_numpy(float)
    vol_max = pd.Series(vol).rolling(50, min_periods=50).max().shift(1).to_numpy(float)
    rng = h - l
    climax = (vol >= 2.0 * vol_sma) & (vol >= 0.9 * vol_max) & (rng <= 0.7 * a) & np.isfinite(a)
    # signal on next bar after climax (causal: know climax only after bar close)
    climax_prev = np.roll(climax, 1)
    climax_prev[0] = False
    uptrend_prev = np.roll(c > e50, 1)
    dntrend_prev = np.roll(c < e50, 1)
    uptrend_prev[0] = dntrend_prev[0] = False
    short_sig = climax_prev & uptrend_prev  # bull climax → short
    long_sig = climax_prev & dntrend_prev
    long_sig[:55] = short_sig[:55] = False
    both = long_sig & short_sig
    long_sig[both] = short_sig[both] = False
    stop = np.full(len(out), np.nan)
    target = np.full(len(out), np.nan)
    # stop at climax bar extreme (prior bar)
    stop[short_sig] = np.roll(h, 1)[short_sig] * (1 + 1e-4)
    risk_s = np.maximum(stop[short_sig] - c[short_sig], c[short_sig] * 1e-4)
    target[short_sig] = c[short_sig] - 2.0 * risk_s
    stop[long_sig] = np.roll(l, 1)[long_sig] * (1 - 1e-4)
    risk = np.maximum(c[long_sig] - stop[long_sig], c[long_sig] * 1e-4)
    target[long_sig] = c[long_sig] + 2.0 * risk
    out["long_signal"] = long_sig
    out["short_signal"] = short_sig
    out["stop_price"] = stop
    out["target_price"] = target
    return out


def to_tradesim_signals(feat: pd.DataFrame, symbol: str, max_hold_bars: int = 24) -> list[Signal]:
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
                    tag="tsm_vol_climax",
                )
            )
    return sigs
