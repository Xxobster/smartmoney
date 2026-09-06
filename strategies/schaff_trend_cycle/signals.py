"""Schaff Trend Cycle 23/50/10, cross 25/75. Vectorized."""

from __future__ import annotations

import numpy as np
import pandas as pd

from strategies.common.signal_sides import SideMode
from tradesim import Signal

STRATEGY_ID = "schaff_trend_cycle"
STRATEGY_VERSION = "0.1.0"

FAST = 23
SLOW = 50
CYCLE = 10
D_N = 3
ATR_N = 14
ATR_STOP = 2.0
RR = 1.5
LO = 25.0
HI = 75.0
WARMUP = SLOW + 2 * CYCLE + 2 * D_N + ATR_N


def _atr(high: np.ndarray, low: np.ndarray, close: np.ndarray, n: int) -> np.ndarray:
    prev_c = np.roll(close, 1)
    prev_c[0] = close[0]
    tr = np.maximum(high - low, np.maximum(np.abs(high - prev_c), np.abs(low - prev_c)))
    return pd.Series(tr).ewm(alpha=1.0 / n, adjust=False, min_periods=n).mean().to_numpy(float)


def _stoch_self(x: pd.Series, n: int) -> pd.Series:
    lo = x.rolling(n, min_periods=n).min()
    hi = x.rolling(n, min_periods=n).max()
    den = (hi - lo).replace(0.0, np.nan)
    k = 100.0 * (x - lo) / den
    return k.clip(0.0, 100.0).ffill()


def schaff_stc(close: np.ndarray) -> np.ndarray:
    s = pd.Series(close, dtype=float)
    macd = s.ewm(span=FAST, adjust=False, min_periods=FAST).mean() - s.ewm(
        span=SLOW, adjust=False, min_periods=SLOW
    ).mean()
    d1 = _stoch_self(macd, CYCLE).ewm(span=D_N, adjust=False, min_periods=D_N).mean()
    d2 = _stoch_self(d1, CYCLE).ewm(span=D_N, adjust=False, min_periods=D_N).mean()
    return d2.clip(0.0, 100.0).to_numpy(float)


def build_signal_frame(df: pd.DataFrame) -> pd.DataFrame:
    out = df.sort_values("ts_ms").reset_index(drop=True).copy()
    h = out["high"].to_numpy(float)
    low = out["low"].to_numpy(float)
    c = out["close"].to_numpy(float)
    stc = schaff_stc(c)
    prev = np.roll(stc, 1)
    prev[0] = np.nan
    long_raw = (prev <= LO) & (stc > LO)
    short_raw = (prev >= HI) & (stc < HI)
    long_raw[:WARMUP] = False
    short_raw[:WARMUP] = False
    both = long_raw & short_raw
    long_raw[both] = short_raw[both] = False
    atr = _atr(h, low, c, ATR_N)
    stop = np.full(len(out), np.nan)
    target = np.full(len(out), np.nan)
    stop[long_raw] = c[long_raw] - ATR_STOP * atr[long_raw]
    target[long_raw] = c[long_raw] + RR * ATR_STOP * atr[long_raw]
    stop[short_raw] = c[short_raw] + ATR_STOP * atr[short_raw]
    target[short_raw] = c[short_raw] - RR * ATR_STOP * atr[short_raw]
    out["stc"] = stc
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
                    tag="stc_l",
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
                    tag="stc_s",
                )
            )
    return sigs
