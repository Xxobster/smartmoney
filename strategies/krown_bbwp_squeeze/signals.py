"""Krown Bollinger Band Width Percentile squeeze + 200 SMA trend — vectorized, causal.

Fair H0 frozen from Krown `kcMnnQr1VFg` + `hNfjyrJEytI` *before* any look at our
Profit Factor (PF):
- 4-hour only (his Bitcoin higher-timeframe BBWP settings)
- Bollinger basis length 7, 2 standard deviations, Simple Moving Average (SMA)
- Bandwidth percentile lookback 100; 5-period SMA of that percentile
- Direction: close vs SMA 200 on the same 4-hour chart
- Long: close > SMA 200 and 5-SMA of BBWP crosses up through 25 (squeeze ending)
- Short: close < SMA 200 and the same squeeze-release cross
- Stop 2 × Average True Range (ATR) 14; take-profit 2R (our exit freeze; video had none)
- Do not search 25/85, lookback, or SMA length after viewing results
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from numpy.lib.stride_tricks import sliding_window_view

from strategies.common.signal_sides import SideMode
from tradesim import Signal

STRATEGY_ID = "krown_bbwp_squeeze"
STRATEGY_VERSION = "0.1.0"

BB_N = 7
BB_K = 2.0
PCT_N = 100
PCT_SMA = 5
SMA_TREND = 200
SQUEEZE_OFF = 25.0
ATR_N = 14
ATR_STOP = 2.0
RR = 2.0
WARMUP = SMA_TREND + PCT_N + PCT_SMA + ATR_N


def _atr(high: np.ndarray, low: np.ndarray, close: np.ndarray, n: int) -> np.ndarray:
    prev_c = np.roll(close, 1)
    prev_c[0] = close[0]
    tr = np.maximum(high - low, np.maximum(np.abs(high - prev_c), np.abs(low - prev_c)))
    return pd.Series(tr).ewm(alpha=1.0 / n, adjust=False, min_periods=n).mean().to_numpy(float)


def _rolling_percentile(x: np.ndarray, n: int) -> np.ndarray:
    """Percent of the last n values that are <= the current value (includes current)."""
    out = np.full(len(x), np.nan)
    if len(x) < n:
        return out
    w = sliding_window_view(x, n)
    last = w[:, -1:]
    out[n - 1 :] = (w <= last).mean(axis=1) * 100.0
    return out


def build_signal_frame(df: pd.DataFrame) -> pd.DataFrame:
    out = df.sort_values("ts_ms").reset_index(drop=True).copy()
    h = out["high"].to_numpy(float)
    low = out["low"].to_numpy(float)
    c = out["close"].to_numpy(float)
    mid = pd.Series(c).rolling(BB_N, min_periods=BB_N).mean().to_numpy(float)
    sd = pd.Series(c).rolling(BB_N, min_periods=BB_N).std(ddof=0).to_numpy(float)
    width = (2.0 * BB_K * sd) / np.where(np.abs(mid) > 1e-12, np.abs(mid), np.nan)
    bbwp = _rolling_percentile(width, PCT_N)
    bbwp_s = pd.Series(bbwp).rolling(PCT_SMA, min_periods=PCT_SMA).mean().to_numpy(float)
    sma = pd.Series(c).rolling(SMA_TREND, min_periods=SMA_TREND).mean().to_numpy(float)
    atr = _atr(h, low, c, ATR_N)
    prev = np.roll(bbwp_s, 1)
    prev[0] = np.nan
    release = (bbwp_s > SQUEEZE_OFF) & (prev <= SQUEEZE_OFF)
    long_raw = release & (c > sma)
    short_raw = release & (c < sma)
    both = long_raw & short_raw
    long_raw[both] = short_raw[both] = False
    long_raw[:WARMUP] = short_raw[:WARMUP] = False
    finite = np.isfinite(bbwp_s) & np.isfinite(sma) & np.isfinite(atr)
    long_raw &= finite
    short_raw &= finite
    stop = np.full(len(out), np.nan)
    target = np.full(len(out), np.nan)
    stop[long_raw] = c[long_raw] - ATR_STOP * atr[long_raw]
    target[long_raw] = c[long_raw] + RR * (c[long_raw] - stop[long_raw])
    stop[short_raw] = c[short_raw] + ATR_STOP * atr[short_raw]
    target[short_raw] = c[short_raw] - RR * (stop[short_raw] - c[short_raw])
    out["bbwp"] = bbwp
    out["bbwp_sma5"] = bbwp_s
    out["sma200"] = sma
    out["atr14"] = atr
    out["long_signal"] = long_raw
    out["short_signal"] = short_raw
    out["stop_price"] = stop
    out["target_price"] = target
    return out


def to_tradesim_signals(
    feat: pd.DataFrame,
    symbol: str,
    max_hold_bars: int = 48,
    *,
    side_mode: SideMode = "long",
) -> list[Signal]:
    sigs: list[Signal] = []
    ts = feat["ts_ms"].to_numpy(np.int64)
    long_sig = feat["long_signal"].to_numpy(bool)
    short_sig = feat["short_signal"].to_numpy(bool)
    stop = feat["stop_price"].to_numpy(float)
    target = feat["target_price"].to_numpy(float)
    px = feat["close"].to_numpy(float)
    use_long = side_mode in ("long", "long_mirror")
    use_short = side_mode in ("short", "short_mirror")
    for i in range(len(feat)):
        p = float(px[i])
        sp = float(stop[i])
        tp = float(target[i])
        if use_long and long_sig[i]:
            if not (np.isfinite(sp) and np.isfinite(tp) and sp < p < tp):
                continue
            sigs.append(
                Signal(
                    ts_ms=int(ts[i]),
                    side=1,
                    symbol=symbol,
                    stop_price=sp,
                    target_price=tp,
                    max_hold_bars=max_hold_bars,
                    tag="bbwp_l",
                )
            )
        elif use_short and short_sig[i]:
            if not (np.isfinite(sp) and np.isfinite(tp) and tp < p < sp):
                continue
            sigs.append(
                Signal(
                    ts_ms=int(ts[i]),
                    side=-1,
                    symbol=symbol,
                    stop_price=sp,
                    target_price=tp,
                    max_hold_bars=max_hold_bars,
                    tag="bbwp_s",
                )
            )
    return sigs
