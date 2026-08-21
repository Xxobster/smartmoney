"""Monday range: 1h close outside then back inside, daily SuperTrend bias."""

from __future__ import annotations

import numpy as np
import pandas as pd

from tradesim import Signal

STRATEGY_ID = "monday_range_sweep"
STRATEGY_VERSION = "0.1.0"

ST_ATR = 10
ST_K = 3.0
MIN_R = 2.0
WARMUP_DAYS = 30


def _supertrend_dir(high: np.ndarray, low: np.ndarray, close: np.ndarray) -> np.ndarray:
    n = len(close)
    prev_c = np.roll(close, 1)
    prev_c[0] = close[0]
    tr = np.maximum(high - low, np.maximum(np.abs(high - prev_c), np.abs(low - prev_c)))
    atr = pd.Series(tr).ewm(alpha=1.0 / ST_ATR, adjust=False, min_periods=1).mean().to_numpy(float)
    hl2 = (high + low) / 2.0
    basic_ub = hl2 + ST_K * atr
    basic_lb = hl2 - ST_K * atr
    fu = np.copy(basic_ub)
    fl = np.copy(basic_lb)
    direction = np.ones(n, dtype=np.int8)
    start = ST_ATR
    for i in range(start, n):
        prev_fu = fu[i - 1]
        prev_fl = fl[i - 1]
        fu[i] = basic_ub[i] if (basic_ub[i] < prev_fu or close[i - 1] > prev_fu) else prev_fu
        fl[i] = basic_lb[i] if (basic_lb[i] > prev_fl or close[i - 1] < prev_fl) else prev_fl
        if close[i] > fu[i - 1]:
            direction[i] = 1
        elif close[i] < fl[i - 1]:
            direction[i] = -1
        else:
            direction[i] = direction[i - 1]
    direction[:start] = 0
    return direction


def _daily_bias(ts_ms: np.ndarray, high: np.ndarray, low: np.ndarray, close: np.ndarray) -> np.ndarray:
    idx = pd.to_datetime(ts_ms, unit="ms", utc=True)
    d = pd.DataFrame({"h": high, "l": low, "c": close}, index=idx)
    daily = d.resample("1D").agg(h=("h", "max"), l=("l", "min"), c=("c", "last")).dropna()
    if len(daily) < ST_ATR + 2:
        return np.zeros(len(ts_ms), dtype=np.int8)
    st = _supertrend_dir(daily["h"].to_numpy(float), daily["l"].to_numpy(float), daily["c"].to_numpy(float))
    daily = daily.copy()
    daily["st"] = st
    daily["st_use"] = daily["st"].shift(1)
    mapped = daily["st_use"].reindex(idx.normalize(), method="ffill")
    return pd.Series(mapped.to_numpy(), dtype=float).fillna(0).to_numpy()


def build_signal_frame(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy().reset_index(drop=True)
    ts = out["ts_ms"].to_numpy(np.int64)
    h = out["high"].to_numpy(float)
    low = out["low"].to_numpy(float)
    c = out["close"].to_numpy(float)
    ny = pd.to_datetime(ts, unit="ms", utc=True).tz_convert("America/New_York")
    wd = ny.weekday.to_numpy()
    week = (ny.isocalendar().week.astype(np.int32) + ny.year.astype(np.int32) * 100).to_numpy()
    is_mon = wd == 0
    mon_h = pd.Series(np.where(is_mon, h, np.nan)).groupby(week).transform("max").to_numpy(float)
    mon_l = pd.Series(np.where(is_mon, low, np.nan)).groupby(week).transform("min").to_numpy(float)
    mon_h = np.where(is_mon, np.nan, mon_h)
    mon_l = np.where(is_mon, np.nan, mon_l)
    # range only valid after Monday (Tue=1 .. Thu=3)
    tradable = (wd >= 1) & (wd <= 3) & np.isfinite(mon_h) & np.isfinite(mon_l) & (mon_h > mon_l)
    outside_hi = tradable & (c > mon_h)
    outside_lo = tradable & (c < mon_l)
    swept_hi = pd.Series(outside_hi).groupby(week).cummax().to_numpy(bool)
    swept_lo = pd.Series(outside_lo).groupby(week).cummax().to_numpy(bool)
    back_in = tradable & (c <= mon_h) & (c >= mon_l)
    short_raw = swept_hi & back_in
    long_raw = swept_lo & back_in
    prev_s = np.roll(short_raw, 1)
    prev_l = np.roll(long_raw, 1)
    prev_s[0] = prev_l[0] = False
    week_chg = np.roll(week, 1)
    week_chg[0] = week[0] - 1
    short_sig = short_raw & ~prev_s
    long_sig = long_raw & ~prev_l
    short_sig[week != week_chg] = short_raw[week != week_chg]
    long_sig[week != week_chg] = long_raw[week != week_chg]
    # first back-in only: keep first True per week
    short_sig = short_sig & ~pd.Series(short_sig).groupby(week).cumsum().gt(1).to_numpy()
    long_sig = long_sig & ~pd.Series(long_sig).groupby(week).cumsum().gt(1).to_numpy()
    bias = _daily_bias(ts, h, low, c)
    long_sig = long_sig & (bias > 0)
    short_sig = short_sig & (bias < 0)
    stop = np.full(len(out), np.nan)
    target = np.full(len(out), np.nan)
    stop[long_sig] = low[long_sig]
    target[long_sig] = mon_h[long_sig]
    stop[short_sig] = h[short_sig]
    target[short_sig] = mon_l[short_sig]
    risk = np.where(long_sig, c - stop, np.where(short_sig, stop - c, np.nan))
    reward = np.where(long_sig, target - c, np.where(short_sig, c - target, np.nan))
    rr_ok = np.isfinite(risk) & (risk > 0) & (reward / np.maximum(risk, 1e-12) >= MIN_R)
    long_sig = long_sig & rr_ok
    short_sig = short_sig & rr_ok
    stop = np.where(long_sig, low, np.where(short_sig, h, np.nan))
    target = np.where(long_sig, mon_h, np.where(short_sig, mon_l, np.nan))
    long_sig[: 24 * WARMUP_DAYS] = False
    short_sig[: 24 * WARMUP_DAYS] = False
    out["monday_high"] = mon_h
    out["monday_low"] = mon_l
    out["daily_st"] = bias
    out["long_signal"] = long_sig
    out["short_signal"] = short_sig
    out["stop_price"] = stop
    out["target_price"] = target
    return out


def to_tradesim_signals(feat: pd.DataFrame, symbol: str, max_hold_bars: int = 96) -> list[Signal]:
    sigs: list[Signal] = []
    ts = feat["ts_ms"].to_numpy(np.int64)
    long_sig = feat["long_signal"].to_numpy(bool)
    short_sig = feat["short_signal"].to_numpy(bool)
    stop = feat["stop_price"].to_numpy(float)
    target = feat["target_price"].to_numpy(float)
    px = feat["close"].to_numpy(float)
    for i in range(len(feat)):
        p = float(px[i])
        if long_sig[i]:
            sp, tp = float(stop[i]), float(target[i])
            if sp < p < tp:
                sigs.append(
                    Signal(
                        ts_ms=int(ts[i]),
                        side=1,
                        symbol=symbol,
                        stop_price=sp,
                        target_price=tp,
                        max_hold_bars=max_hold_bars,
                        tag="mon_rng_l",
                    )
                )
        elif short_sig[i]:
            sp, tp = float(stop[i]), float(target[i])
            if tp < p < sp:
                sigs.append(
                    Signal(
                        ts_ms=int(ts[i]),
                        side=-1,
                        symbol=symbol,
                        stop_price=sp,
                        target_price=tp,
                        max_hold_bars=max_hold_bars,
                        tag="mon_rng_s",
                    )
                )
    return sigs
