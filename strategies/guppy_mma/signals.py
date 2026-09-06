"""Guppy Multiple Moving Average full-ribbon separation. Vectorized."""

from __future__ import annotations

import numpy as np
import pandas as pd

from strategies.common.signal_sides import SideMode
from tradesim import Signal

STRATEGY_ID = "guppy_mma"
STRATEGY_VERSION = "0.1.0"

SHORT_N = (3, 5, 8, 10, 12, 15)
LONG_N = (30, 35, 40, 45, 50, 60)
ATR_N = 14
ATR_STOP = 2.0
RR = 1.5
WARMUP = 60 + ATR_N + 2


def _atr(high: np.ndarray, low: np.ndarray, close: np.ndarray, n: int) -> np.ndarray:
    prev_c = np.roll(close, 1)
    prev_c[0] = close[0]
    tr = np.maximum(high - low, np.maximum(np.abs(high - prev_c), np.abs(low - prev_c)))
    return pd.Series(tr).ewm(alpha=1.0 / n, adjust=False, min_periods=n).mean().to_numpy(float)


def build_signal_frame(df: pd.DataFrame) -> pd.DataFrame:
    out = df.sort_values("ts_ms").reset_index(drop=True).copy()
    h = out["high"].to_numpy(float)
    low = out["low"].to_numpy(float)
    c = out["close"].to_numpy(float)
    s = pd.Series(c)
    short_stack = np.column_stack(
        [s.ewm(span=n, adjust=False, min_periods=n).mean().to_numpy(float) for n in SHORT_N]
    )
    long_stack = np.column_stack(
        [s.ewm(span=n, adjust=False, min_periods=n).mean().to_numpy(float) for n in LONG_N]
    )
    short_lo = short_stack.min(axis=1)
    short_hi = short_stack.max(axis=1)
    long_lo = long_stack.min(axis=1)
    long_hi = long_stack.max(axis=1)
    bull = short_lo > long_hi
    bear = short_hi < long_lo
    long_raw = bull & ~np.roll(bull, 1)
    short_raw = bear & ~np.roll(bear, 1)
    long_raw[0] = short_raw[0] = False
    long_raw[:WARMUP] = short_raw[:WARMUP] = False
    both = long_raw & short_raw
    long_raw[both] = short_raw[both] = False
    atr = _atr(h, low, c, ATR_N)
    stop = np.full(len(out), np.nan)
    target = np.full(len(out), np.nan)
    stop[long_raw] = c[long_raw] - ATR_STOP * atr[long_raw]
    target[long_raw] = c[long_raw] + RR * ATR_STOP * atr[long_raw]
    stop[short_raw] = c[short_raw] + ATR_STOP * atr[short_raw]
    target[short_raw] = c[short_raw] - RR * ATR_STOP * atr[short_raw]
    out["guppy_short_lo"] = short_lo
    out["guppy_long_hi"] = long_hi
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
                    tag="gup_l",
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
                    tag="gup_s",
                )
            )
    return sigs
