"""Vectorized RSI(3)+ADX(5)+EMA50 scalp signals."""

from __future__ import annotations

import numpy as np
import pandas as pd

from tradesim import Signal

STRATEGY_ID = "tsm_rsi_adx_ema_scalp"
STRATEGY_VERSION = "0.1.0"


def ema(x: np.ndarray, n: int) -> np.ndarray:
    return pd.Series(x).ewm(span=n, adjust=False).mean().to_numpy(float)


def wilder_rsi(close: np.ndarray, length: int = 3) -> np.ndarray:
    c = pd.Series(close, dtype=float)
    d = c.diff()
    gain = d.clip(lower=0.0)
    loss = (-d).clip(lower=0.0)
    avg_g = gain.ewm(alpha=1.0 / length, adjust=False, min_periods=length).mean()
    avg_l = loss.ewm(alpha=1.0 / length, adjust=False, min_periods=length).mean()
    rs = avg_g / avg_l.replace(0.0, np.nan)
    return (100.0 - (100.0 / (1.0 + rs))).to_numpy(float)


def wilder_adx(high: np.ndarray, low: np.ndarray, close: np.ndarray, length: int = 5) -> np.ndarray:
    h = pd.Series(high, dtype=float)
    l = pd.Series(low, dtype=float)
    c = pd.Series(close, dtype=float)
    up = h.diff()
    dn = -l.diff()
    plus_dm = pd.Series(np.where((up > dn) & (up > 0), up, 0.0))
    minus_dm = pd.Series(np.where((dn > up) & (dn > 0), dn, 0.0))
    tr = pd.concat([(h - l), (h - c.shift()).abs(), (l - c.shift()).abs()], axis=1).max(axis=1)
    atr = tr.ewm(alpha=1.0 / length, adjust=False, min_periods=length).mean()
    plus_di = 100 * plus_dm.ewm(alpha=1.0 / length, adjust=False, min_periods=length).mean() / atr
    minus_di = 100 * minus_dm.ewm(alpha=1.0 / length, adjust=False, min_periods=length).mean() / atr
    dx = (100 * (plus_di - minus_di).abs() / (plus_di + minus_di).replace(0.0, np.nan))
    return dx.ewm(alpha=1.0 / length, adjust=False, min_periods=length).mean().to_numpy(float)


def build_signal_frame(df: pd.DataFrame, *, session_filter: bool = True) -> pd.DataFrame:
    out = df.copy().reset_index(drop=True)
    close = out["close"].to_numpy(float)
    high = out["high"].to_numpy(float)
    low = out["low"].to_numpy(float)
    e50 = ema(close, 50)
    rsi = wilder_rsi(close, 3)
    adx = wilder_adx(high, low, close, 5)
    out["ema50"] = e50
    out["rsi3"] = rsi
    out["adx5"] = adx

    sess = np.ones(len(out), dtype=bool)
    if session_filter:
        hours = ((out["ts_ms"].to_numpy(np.int64) // 3_600_000) % 24).astype(int)
        sess = (hours >= 7) & (hours < 21)

    long_raw = sess & (close > e50) & (rsi <= 20.0) & (adx > 30.0)
    short_raw = sess & (close < e50) & (rsi >= 80.0) & (adx > 30.0)
    # edge trigger
    long_sig = long_raw & ~np.roll(long_raw, 1)
    short_sig = short_raw & ~np.roll(short_raw, 1)
    long_sig[0] = short_sig[0] = False

    stop = np.full(len(out), np.nan)
    target = np.full(len(out), np.nan)
    stop[long_sig] = low[long_sig] * (1 - 1e-4)
    risk_l = np.maximum(close[long_sig] - stop[long_sig], close[long_sig] * 1e-4)
    target[long_sig] = close[long_sig] + 1.0 * risk_l
    stop[short_sig] = high[short_sig] * (1 + 1e-4)
    risk_s = np.maximum(stop[short_sig] - close[short_sig], close[short_sig] * 1e-4)
    target[short_sig] = close[short_sig] - 1.0 * risk_s

    out["long_signal"] = long_sig
    out["short_signal"] = short_sig
    out["stop_price"] = stop
    out["target_price"] = target
    return out


def to_tradesim_signals(feat: pd.DataFrame, symbol: str, max_hold_bars: int = 24) -> list[Signal]:
    sigs: list[Signal] = []
    ts = feat["ts_ms"].to_numpy(np.int64)
    for i in range(len(feat)):
        if bool(feat["long_signal"].iloc[i]) ^ bool(feat["short_signal"].iloc[i]):
            side = 1 if bool(feat["long_signal"].iloc[i]) else -1
            sp, tp = float(feat["stop_price"].iloc[i]), float(feat["target_price"].iloc[i])
            if np.isnan(sp) or np.isnan(tp):
                continue
            sigs.append(
                Signal(
                    ts_ms=int(ts[i]),
                    side=side,
                    symbol=symbol,
                    stop_price=sp,
                    target_price=tp,
                    max_hold_bars=max_hold_bars,
                    tag="tsm_rsi_adx",
                )
            )
    return sigs
