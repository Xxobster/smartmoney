"""Monthly classic pivot + Bollinger(50,2) confluence (causal)."""

from __future__ import annotations

import numpy as np
import pandas as pd

from tradesim import Signal

STRATEGY_ID = "tsm_pivot_bb"
STRATEGY_VERSION = "0.1.0"


def monthly_pivots(ts_ms: np.ndarray, high: np.ndarray, low: np.ndarray, close: np.ndarray, open_: np.ndarray) -> np.ndarray:
    """Prior completed month classic pivot P = (H+L+C)/3, forward-filled."""
    idx = pd.to_datetime(ts_ms, unit="ms", utc=True).tz_localize(None)
    df = pd.DataFrame({"ts": idx, "h": high, "l": low, "c": close, "o": open_})
    df["ym"] = df["ts"].dt.to_period("M")
    # monthly OHLC of each calendar month
    g = df.groupby("ym", sort=True)
    m = g.agg(h=("h", "max"), l=("l", "min"), c=("c", "last"), o=("o", "first"))
    m["P"] = (m["h"] + m["l"] + m["c"]) / 3.0
    # use prior month's pivot for current month
    m["P_use"] = m["P"].shift(1)
    # map back
    use = df["ym"].map(m["P_use"]).to_numpy(float)
    return use


def build_signal_frame(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy().reset_index(drop=True)
    ts = out["ts_ms"].to_numpy(np.int64)
    o = out["open"].to_numpy(float)
    h = out["high"].to_numpy(float)
    l = out["low"].to_numpy(float)
    c = out["close"].to_numpy(float)
    pivot = monthly_pivots(ts, h, l, c, o)
    mid = pd.Series(c).rolling(50, min_periods=50).mean().to_numpy(float)
    std = pd.Series(c).rolling(50, min_periods=50).std(ddof=0).to_numpy(float)
    upper = mid + 2.0 * std
    lower = mid - 2.0 * std
    touch_lower = l <= lower
    touch_mid = (l <= mid) & (h >= mid)
    touch_upper = h >= upper
    bull = c > o
    bear = c < o
    long_raw = np.isfinite(pivot) & np.isfinite(mid) & (c > pivot) & (touch_lower | touch_mid) & bull
    short_raw = np.isfinite(pivot) & np.isfinite(mid) & (c < pivot) & (touch_upper | touch_mid) & bear
    long_sig = long_raw & ~np.roll(long_raw, 1)
    short_sig = short_raw & ~np.roll(short_raw, 1)
    long_sig[0] = short_sig[0] = False
    long_sig[:60] = short_sig[:60] = False
    both = long_sig & short_sig
    long_sig[both] = short_sig[both] = False

    stop = np.full(len(out), np.nan)
    target = np.full(len(out), np.nan)
    stop[long_sig] = l[long_sig] * (1 - 1e-4)
    risk = np.maximum(c[long_sig] - stop[long_sig], c[long_sig] * 1e-4)
    target[long_sig] = c[long_sig] + 2.0 * risk
    stop[short_sig] = h[short_sig] * (1 + 1e-4)
    risk_s = np.maximum(stop[short_sig] - c[short_sig], c[short_sig] * 1e-4)
    target[short_sig] = c[short_sig] - 2.0 * risk_s

    out["monthly_pivot"] = pivot
    out["bb_mid"] = mid
    out["bb_upper"] = upper
    out["bb_lower"] = lower
    out["long_signal"] = long_sig
    out["short_signal"] = short_sig
    out["stop_price"] = stop
    out["target_price"] = target
    return out


def to_tradesim_signals(feat: pd.DataFrame, symbol: str, max_hold_bars: int = 20) -> list[Signal]:
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
                    tag="tsm_pivot_bb",
                )
            )
    return sigs
