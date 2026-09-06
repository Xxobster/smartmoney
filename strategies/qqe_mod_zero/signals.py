"""QQE MOD zero-line + Exponential Moving Average 200. Vectorized."""

from __future__ import annotations

import numpy as np
import pandas as pd

from strategies.common.qqe import qqe_mod_zero_line
from strategies.common.signal_sides import SideMode
from tradesim import Signal

STRATEGY_ID = "qqe_mod_zero"
STRATEGY_VERSION = "0.1.0"

RSI_N = 6
SF = 5
EMA_N = 200
SWING_N = 10
RR = 1.5
WARMUP = EMA_N + RSI_N + SF + SWING_N + 2


def build_signal_frame(df: pd.DataFrame) -> pd.DataFrame:
    out = df.sort_values("ts_ms").reset_index(drop=True).copy()
    h = out["high"].to_numpy(float)
    low = out["low"].to_numpy(float)
    c = out["close"].to_numpy(float)
    qqe = qqe_mod_zero_line(c, rsi_n=RSI_N, sf=SF)
    prev = np.roll(qqe, 1)
    prev[0] = np.nan
    ema = pd.Series(c).ewm(span=EMA_N, adjust=False, min_periods=EMA_N).mean().to_numpy(float)
    swing_lo = pd.Series(low).rolling(SWING_N, min_periods=SWING_N).min().shift(1).to_numpy(float)
    swing_hi = pd.Series(h).rolling(SWING_N, min_periods=SWING_N).max().shift(1).to_numpy(float)
    long_raw = (c > ema) & (prev <= 0.0) & (qqe > 0.0)
    short_raw = (c < ema) & (prev >= 0.0) & (qqe < 0.0)
    long_raw[:WARMUP] = False
    short_raw[:WARMUP] = False
    both = long_raw & short_raw
    long_raw[both] = short_raw[both] = False
    stop = np.full(len(out), np.nan)
    target = np.full(len(out), np.nan)
    stop[long_raw] = swing_lo[long_raw]
    risk_l = c[long_raw] - swing_lo[long_raw]
    target[long_raw] = c[long_raw] + RR * risk_l
    stop[short_raw] = swing_hi[short_raw]
    risk_s = swing_hi[short_raw] - c[short_raw]
    target[short_raw] = c[short_raw] - RR * risk_s
    out["qqe_zero"] = qqe
    out["ema200"] = ema
    out["long_signal"] = long_raw
    out["short_signal"] = short_raw
    out["stop_price"] = stop
    out["target_price"] = target
    return out


def to_tradesim_signals(
    feat: pd.DataFrame,
    symbol: str,
    max_hold_bars: int = 96,
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
                    tag="qqe_l",
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
                    tag="qqe_s",
                )
            )
    return sigs
