"""Causal Heikin Ashi wedge breaks confirmed by EMA50."""

from __future__ import annotations

import numpy as np
import pandas as pd
from numpy.lib.stride_tricks import sliding_window_view

from tradesim import Signal

STRATEGY_ID = "tsm_heikin_ashi_ema50"
STRATEGY_VERSION = "0.1.0"
WEDGE_WINDOW = 30


def ema(x: np.ndarray, n: int) -> np.ndarray:
    return pd.Series(x).ewm(span=n, adjust=False).mean().to_numpy(float)


def heikin_ashi(o: np.ndarray, h: np.ndarray, l: np.ndarray, c: np.ndarray) -> tuple[np.ndarray, ...]:
    n = len(c)
    ha_c = (o + h + l + c) / 4.0
    ha_o = np.empty(n, dtype=float)
    ha_o[0] = (o[0] + c[0]) / 2.0
    # causal recurrence — sequential dependency by definition
    for i in range(1, n):
        ha_o[i] = (ha_o[i - 1] + ha_c[i - 1]) / 2.0
    ha_h = np.maximum(h, np.maximum(ha_o, ha_c))
    ha_l = np.minimum(l, np.minimum(ha_o, ha_c))
    return ha_o, ha_h, ha_l, ha_c


def _rolling_slope_intercept(y: np.ndarray, w: int) -> tuple[np.ndarray, np.ndarray]:
    """Least-squares slope/intercept for each trailing window; aligned to window end."""
    n = len(y)
    slope = np.full(n, np.nan)
    intercept = np.full(n, np.nan)
    if n < w:
        return slope, intercept
    win = sliding_window_view(y, w)  # (n-w+1, w)
    x = np.arange(w, dtype=float)
    xm = x.mean()
    denom = float(((x - xm) ** 2).sum())
    ym = win.mean(axis=1)
    sl = ((win - ym[:, None]) * (x - xm)).sum(axis=1) / denom
    ic = ym - sl * xm
    slope[w - 1 :] = sl
    intercept[w - 1 :] = ic
    return slope, intercept


def build_signal_frame(df: pd.DataFrame, *, window: int = WEDGE_WINDOW) -> pd.DataFrame:
    out = df.copy().reset_index(drop=True)
    o = out["open"].to_numpy(float)
    h = out["high"].to_numpy(float)
    l = out["low"].to_numpy(float)
    c = out["close"].to_numpy(float)
    n = len(out)

    ha_o, ha_h, ha_l, ha_c = heikin_ashi(o, h, l, c)
    e50 = ema(ha_c, 50)
    out["ha_open"] = ha_o
    out["ha_high"] = ha_h
    out["ha_low"] = ha_l
    out["ha_close"] = ha_c
    out["ema50_ha"] = e50

    sh, ih = _rolling_slope_intercept(ha_h, window)
    sl, il = _rolling_slope_intercept(ha_l, window)
    x_end = float(window - 1)
    res_end = ih + sh * x_end  # fitted high line at end
    sup_end = il + sl * x_end  # fitted low line at end
    width_end = res_end - sup_end
    width_start = (ih + sh * 0.0) - (il + sl * 0.0)

    rising = (sh > 0) & (sl > 0) & (sl > sh) & (width_end > 0) & (width_end < width_start)
    falling = (sh < 0) & (sl < 0) & (sh < sl) & (width_end > 0) & (width_end < width_start)

    # Window extremes for stops / width target
    if n >= window:
        hh = sliding_window_view(ha_h, window).max(axis=1)
        ll = sliding_window_view(ha_l, window).min(axis=1)
        w_hi = np.full(n, np.nan)
        w_lo = np.full(n, np.nan)
        w_hi[window - 1 :] = hh
        w_lo[window - 1 :] = ll
    else:
        w_hi = np.full(n, np.nan)
        w_lo = np.full(n, np.nan)

    wedge_width = np.maximum(w_hi - w_lo, width_start)

    short_raw = rising & (ha_c < sup_end) & (ha_c < e50) & np.isfinite(sup_end)
    long_raw = falling & (ha_c > res_end) & (ha_c > e50) & np.isfinite(res_end)
    # first break only
    short_sig = short_raw & ~np.roll(short_raw, 1)
    long_sig = long_raw & ~np.roll(long_raw, 1)
    short_sig[0] = long_sig[0] = False
    short_sig[: window] = False
    long_sig[: window] = False

    both = long_sig & short_sig
    long_sig[both] = False
    short_sig[both] = False

    stop = np.full(n, np.nan)
    target = np.full(n, np.nan)
    stop[short_sig] = w_hi[short_sig] * (1 + 1e-4)
    risk_s = np.maximum(stop[short_sig] - c[short_sig], c[short_sig] * 1e-4)
    tp_dist_s = np.maximum(2.0 * risk_s, wedge_width[short_sig])
    target[short_sig] = c[short_sig] - tp_dist_s

    stop[long_sig] = w_lo[long_sig] * (1 - 1e-4)
    risk_l = np.maximum(c[long_sig] - stop[long_sig], c[long_sig] * 1e-4)
    tp_dist_l = np.maximum(2.0 * risk_l, wedge_width[long_sig])
    target[long_sig] = c[long_sig] + tp_dist_l

    out["long_signal"] = long_sig
    out["short_signal"] = short_sig
    out["stop_price"] = stop
    out["target_price"] = target
    return out


def to_tradesim_signals(feat: pd.DataFrame, symbol: str, max_hold_bars: int = 64) -> list[Signal]:
    sigs: list[Signal] = []
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
                    tag="tsm_ha_ema50",
                )
            )
    return sigs
