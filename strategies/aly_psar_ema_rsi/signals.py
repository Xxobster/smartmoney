"""Parabolic Stop and Reverse + Exponential Moving Average 200 + RSI H0.

Fair freeze from Aly Trading `RdHzNY0K2ws` (TradeIQ recipe):
- 4-hour only (video reported 5-minute as a loss; do not search timeframe)
- Wilder Parabolic Stop and Reverse (SAR) step 0.02 / max 0.20
- Exponential Moving Average (EMA) 200, Relative Strength Index (RSI) 14 vs 50
- Entry on rising edge into the full condition set (not every bar in-regime)
- Stop: prior 10-bar swing; take-profit 1.5R (SAR flip omitted in tradesim)
- Long and short reported separately
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from strategies.common.signal_sides import SideMode
from tradesim import Signal

STRATEGY_ID = "aly_psar_ema_rsi"
STRATEGY_VERSION = "0.1.0"

PSAR_STEP = 0.02
PSAR_MAX = 0.20
EMA_N = 200
RSI_N = 14
RSI_LEVEL = 50.0
SWING_N = 10
RR = 1.5
WARMUP = EMA_N + RSI_N + SWING_N + 4


def _rsi(close: np.ndarray, n: int) -> np.ndarray:
    d = np.diff(close, prepend=close[0])
    up = np.where(d > 0.0, d, 0.0)
    dn = np.where(d < 0.0, -d, 0.0)
    ru = pd.Series(up).ewm(alpha=1.0 / n, adjust=False, min_periods=n).mean()
    rd = pd.Series(dn).ewm(alpha=1.0 / n, adjust=False, min_periods=n).mean()
    return (100.0 - 100.0 / (1.0 + ru / (rd + 1e-12))).to_numpy(float)


def _psar(high: np.ndarray, low: np.ndarray) -> np.ndarray:
    """Wilder Parabolic Stop and Reverse. Path-dependent; one pass over bars."""
    n = len(high)
    sar = np.full(n, np.nan)
    if n == 0:
        return sar
    bull = True
    af = PSAR_STEP
    ep = float(high[0])
    sar[0] = float(low[0])
    for i in range(1, n):
        prev = float(sar[i - 1])
        if bull:
            cand = prev + af * (ep - prev)
            lo = float(low[i - 1])
            if i >= 2:
                lo = min(lo, float(low[i - 2]))
            cand = min(cand, lo)
            if float(low[i]) < cand:
                bull = False
                sar[i] = ep
                ep = float(low[i])
                af = PSAR_STEP
            else:
                sar[i] = cand
                if float(high[i]) > ep:
                    ep = float(high[i])
                    af = min(af + PSAR_STEP, PSAR_MAX)
        else:
            cand = prev + af * (ep - prev)
            hi = float(high[i - 1])
            if i >= 2:
                hi = max(hi, float(high[i - 2]))
            cand = max(cand, hi)
            if float(high[i]) > cand:
                bull = True
                sar[i] = ep
                ep = float(high[i])
                af = PSAR_STEP
            else:
                sar[i] = cand
                if float(low[i]) < ep:
                    ep = float(low[i])
                    af = min(af + PSAR_STEP, PSAR_MAX)
    return sar


def build_signal_frame(df: pd.DataFrame) -> pd.DataFrame:
    out = df.sort_values("ts_ms").reset_index(drop=True).copy()
    h = out["high"].to_numpy(float)
    low = out["low"].to_numpy(float)
    c = out["close"].to_numpy(float)
    sar = _psar(h, low)
    ema = pd.Series(c).ewm(span=EMA_N, adjust=False, min_periods=EMA_N).mean().to_numpy(float)
    rsi = _rsi(c, RSI_N)
    swing_lo = pd.Series(low).rolling(SWING_N, min_periods=SWING_N).min().shift(1).to_numpy(float)
    swing_hi = pd.Series(h).rolling(SWING_N, min_periods=SWING_N).max().shift(1).to_numpy(float)
    long_on = (c > sar) & (c > ema) & (rsi > RSI_LEVEL)
    short_on = (c < sar) & (c < ema) & (rsi < RSI_LEVEL)
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
    out["psar"] = sar
    out["ema200"] = ema
    out["rsi14"] = rsi
    out["long_signal"] = long_raw
    out["short_signal"] = short_raw
    out["stop_price"] = stop
    out["target_price"] = target
    return out


def to_tradesim_signals(
    feat: pd.DataFrame,
    symbol: str,
    max_hold_bars: int = 72,
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
                    tag="psar_l",
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
                    tag="psar_s",
                )
            )
    return sigs
