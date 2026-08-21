"""UTC session VWAP + EMA200 trend + swing S/D proxy (causal)."""

from __future__ import annotations

import numpy as np
import pandas as pd

from tradesim import Signal

STRATEGY_ID = "tsm_vwap_sd"
STRATEGY_VERSION = "0.1.0"


def ema(x, n):
    return pd.Series(x).ewm(span=n, adjust=False).mean().to_numpy(float)


def session_vwap(ts_ms, high, low, close, volume):
    typical = (high + low + close) / 3.0
    day = ts_ms // 86_400_000
    pv = typical * volume
    df = pd.DataFrame({"day": day, "pv": pv, "vol": volume})
    g = df.groupby("day", sort=False)
    cum_pv = g["pv"].cumsum().to_numpy(float)
    cum_vol = g["vol"].cumsum().to_numpy(float)
    with np.errstate(divide="ignore", invalid="ignore"):
        return np.where(cum_vol > 0, cum_pv / cum_vol, np.nan)


def build_signal_frame(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy().reset_index(drop=True)
    ts = out["ts_ms"].to_numpy(np.int64)
    h = out["high"].to_numpy(float)
    l = out["low"].to_numpy(float)
    c = out["close"].to_numpy(float)
    vol = out["volume"].to_numpy(float) if "volume" in out.columns else np.ones(len(out))
    vol = np.where(vol > 0, vol, 1.0)
    vwap = session_vwap(ts, h, l, c, vol)
    e200 = ema(c, 200)
    swing_hi = pd.Series(h).rolling(20, min_periods=20).max().shift(1).to_numpy(float)
    swing_lo = pd.Series(l).rolling(20, min_periods=20).min().shift(1).to_numpy(float)
    touched_vwap = np.isfinite(vwap) & ((l <= vwap) | (h >= vwap))
    # reclaim after touch: close on correct side of VWAP while bar tagged VWAP + swing
    long_raw = (c > e200) & touched_vwap & (c > vwap) & (l <= np.minimum(vwap, swing_lo) * 1.002)
    short_raw = (c < e200) & touched_vwap & (c < vwap) & (h >= np.maximum(vwap, swing_hi) * 0.998)
    long_sig = long_raw & ~np.roll(long_raw, 1)
    short_sig = short_raw & ~np.roll(short_raw, 1)
    long_sig[0] = short_sig[0] = False
    long_sig[:200] = short_sig[:200] = False
    both = long_sig & short_sig
    long_sig[both] = short_sig[both] = False

    stop = np.full(len(out), np.nan)
    target = np.full(len(out), np.nan)
    stop[long_sig] = np.minimum(l[long_sig], swing_lo[long_sig]) * (1 - 1e-4)
    risk = np.maximum(c[long_sig] - stop[long_sig], c[long_sig] * 1e-4)
    target[long_sig] = c[long_sig] + 2.0 * risk
    stop[short_sig] = np.maximum(h[short_sig], swing_hi[short_sig]) * (1 + 1e-4)
    risk_s = np.maximum(stop[short_sig] - c[short_sig], c[short_sig] * 1e-4)
    target[short_sig] = c[short_sig] - 2.0 * risk_s

    out["vwap"] = vwap
    out["ema200"] = e200
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
                    tag="tsm_vwap_sd",
                )
            )
    return sigs
