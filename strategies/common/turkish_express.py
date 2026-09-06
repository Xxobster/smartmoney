"""MavilimW + Inverse Fisher Transform (IFT) of Relative Strength Index (RSI).

Public defaults from Kivanc Ozbilgic / Trader's Landing `J3be7tlxB6E`.
Trend filter is either Exponential Moving Average (EMA) 200 or Hull 16.
"""

from __future__ import annotations

from typing import Literal

import numpy as np
import pandas as pd

from strategies.common.signal_sides import SideMode
from strategies.common.wma import hull_moving_average, rolling_wma
from tradesim import Signal

TrendKind = Literal["ema200", "hma16"]

MAV_F = 3
MAV_S = 5
IFT_RSI_N = 5
IFT_WMA_N = 9
EMA_N = 200
HMA_N = 16
SWING_N = 10
RR = 3.0
IFT_LONG_LEVEL = -0.5
IFT_SHORT_LEVEL = -0.5  # video text; not the textbook +0.5 short line
WARMUP = EMA_N + SWING_N + IFT_WMA_N + 4


def _rsi_wilder(close: np.ndarray, n: int) -> np.ndarray:
    d = np.diff(close, prepend=close[0])
    up = np.where(d > 0.0, d, 0.0)
    dn = np.where(d < 0.0, -d, 0.0)
    ru = pd.Series(up).ewm(alpha=1.0 / n, adjust=False, min_periods=n).mean()
    rd = pd.Series(dn).ewm(alpha=1.0 / n, adjust=False, min_periods=n).mean()
    return (100.0 - 100.0 / (1.0 + ru / (rd + 1e-12))).to_numpy(float)


def mavilim_w(close: np.ndarray) -> np.ndarray:
    """Kivanc default First=3, Second=5 nested weighted moving averages."""
    tmal = MAV_F + MAV_S
    fmal = MAV_S + tmal
    ftmal = tmal + fmal
    smal = fmal + ftmal
    m1 = rolling_wma(close, MAV_F)
    m2 = rolling_wma(m1, MAV_S)
    m3 = rolling_wma(m2, tmal)
    m4 = rolling_wma(m3, fmal)
    m5 = rolling_wma(m4, ftmal)
    return rolling_wma(m5, smal)


def ift_rsi(close: np.ndarray) -> np.ndarray:
    rsi = _rsi_wilder(close, IFT_RSI_N)
    v1 = 0.1 * (rsi - 50.0)
    v2 = rolling_wma(v1, IFT_WMA_N)
    return np.tanh(v2)


def build_turkish_signal_frame(
    df: pd.DataFrame,
    *,
    trend: TrendKind = "ema200",
) -> pd.DataFrame:
    out = df.sort_values("ts_ms").reset_index(drop=True).copy()
    h = out["high"].to_numpy(float)
    low = out["low"].to_numpy(float)
    c = out["close"].to_numpy(float)
    mav = mavilim_w(c)
    ift = ift_rsi(c)
    if trend == "hma16":
        line = hull_moving_average(c, HMA_N)
    else:
        line = pd.Series(c).ewm(span=EMA_N, adjust=False, min_periods=EMA_N).mean().to_numpy(
            float
        )
    prev_mav = np.roll(mav, 1)
    prev_mav[0] = np.nan
    blue = mav > prev_mav
    red = mav < prev_mav
    swing_lo = pd.Series(low).rolling(SWING_N, min_periods=SWING_N).min().shift(1).to_numpy(
        float
    )
    swing_hi = pd.Series(h).rolling(SWING_N, min_periods=SWING_N).max().shift(1).to_numpy(
        float
    )
    long_on = (c > line) & blue & (ift > IFT_LONG_LEVEL)
    short_on = (c < line) & red & (ift < IFT_SHORT_LEVEL)
    long_raw = long_on & ~np.roll(long_on, 1)
    short_raw = short_on & ~np.roll(short_on, 1)
    long_raw[0] = short_raw[0] = False
    long_raw[:WARMUP] = short_raw[:WARMUP] = False
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
    out["mavilim"] = mav
    out["ift"] = ift
    out["trend_line"] = line
    out["long_signal"] = long_raw
    out["short_signal"] = short_raw
    out["stop_price"] = stop
    out["target_price"] = target
    return out


def to_turkish_tradesim_signals(
    feat: pd.DataFrame,
    symbol: str,
    max_hold_bars: int,
    *,
    side_mode: SideMode = "long",
    tag_prefix: str = "te",
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
                    tag=f"{tag_prefix}_l",
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
                    tag=f"{tag_prefix}_s",
                )
            )
    return sigs
