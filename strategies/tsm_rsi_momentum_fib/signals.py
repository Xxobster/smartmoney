"""Vectorized H0 signals: RSI momentum arm → Fib pullback → rejection."""

from __future__ import annotations

import numpy as np
import pandas as pd

from tradesim import Signal

STRATEGY_ID = "tsm_rsi_momentum_fib"
STRATEGY_VERSION = "0.1.0"


def wilder_rsi(close: np.ndarray, length: int = 14) -> np.ndarray:
    """Causal Wilder RSI via EWM(alpha=1/length); NaN until warm-up."""
    c = pd.Series(np.asarray(close, dtype=float))
    delta = c.diff()
    gain = delta.clip(lower=0.0)
    loss = (-delta).clip(lower=0.0)
    avg_g = gain.ewm(alpha=1.0 / length, adjust=False, min_periods=length).mean()
    avg_l = loss.ewm(alpha=1.0 / length, adjust=False, min_periods=length).mean()
    rs = avg_g / avg_l.replace(0.0, np.nan)
    out = (100.0 - (100.0 / (1.0 + rs))).to_numpy(dtype=float)
    return out


def ema(close: np.ndarray, length: int = 50) -> np.ndarray:
    return pd.Series(close).ewm(span=length, adjust=False).mean().to_numpy(dtype=float)


def fractal_swings(high: np.ndarray, low: np.ndarray, left: int = 2, right: int = 2):
    """Confirm swings on bar j = i+right (causal). Returns confirm flags + pivot prices."""
    n = len(high)
    sh = np.zeros(n, dtype=bool)
    sl = np.zeros(n, dtype=bool)
    ph = np.full(n, np.nan)
    pl = np.full(n, np.nan)
    for j in range(left + right, n):
        i = j - right
        wh = high[i - left : j + 1]
        wl = low[i - left : j + 1]
        if high[i] >= wh.max() and int(np.sum(wh == high[i])) == 1:
            sh[j] = True
            ph[j] = high[i]
        if low[i] <= wl.min() and int(np.sum(wl == low[i])) == 1:
            sl[j] = True
            pl[j] = low[i]
    return sh, sl, ph, pl


def build_signal_frame(df: pd.DataFrame) -> pd.DataFrame:
    """Add RSI/EMA/arm/pullback/rejection columns (all causal)."""
    out = df.copy().reset_index(drop=True)
    close = out["close"].to_numpy(float)
    high = out["high"].to_numpy(float)
    low = out["low"].to_numpy(float)
    rsi = wilder_rsi(close, 14)
    e50 = ema(close, 50)
    out["rsi"] = rsi
    out["ema50"] = e50

    # Cross events on closed bar
    rsi_prev = np.roll(rsi, 1)
    rsi_prev[0] = np.nan
    arm_long = (rsi_prev < 70.0) & (rsi >= 70.0)
    arm_short = (rsi_prev > 30.0) & (rsi <= 30.0)
    out["arm_long"] = arm_long
    out["arm_short"] = arm_short

    sh, sl, ph, pl = fractal_swings(high, low, 2, 2)
    last_sh = pd.Series(np.where(sh, ph, np.nan)).ffill().to_numpy()
    last_sl = pd.Series(np.where(sl, pl, np.nan)).ffill().to_numpy()
    out["last_swing_high"] = last_sh
    out["last_swing_low"] = last_sl

    n = len(out)
    long_sig = np.zeros(n, dtype=bool)
    short_sig = np.zeros(n, dtype=bool)
    stop = np.full(n, np.nan)
    target = np.full(n, np.nan)

    # State machine — small and local; vectorized prep above.
    armed_long = False
    armed_short = False
    leg_lo = leg_hi = np.nan
    expire = 0
    max_wait = 48  # bars after arm (~12h on 15m)

    for i in range(n):
        if arm_long[i] and close[i] > e50[i]:
            armed_long = True
            armed_short = False
            leg_lo = last_sl[i]
            leg_hi = high[i]
            expire = i + max_wait
        if arm_short[i] and close[i] < e50[i]:
            armed_short = True
            armed_long = False
            leg_hi = last_sh[i]
            leg_lo = low[i]
            expire = i + max_wait
        if i > expire:
            armed_long = armed_short = False

        if armed_long and not np.isnan(leg_lo) and not np.isnan(leg_hi) and leg_hi > leg_lo:
            span = leg_hi - leg_lo
            fibs = (leg_hi - 0.236 * span, leg_hi - 0.382 * span, leg_hi - 0.50 * span)
            touched = any(low[i] <= f <= high[i] for f in fibs)
            # Rejection: close back in upper half of bar and above lowest fib touched zone
            zone = min(fibs)
            reject = touched and (close[i] > open_safe(out, i)) and (close[i] >= zone)
            if reject:
                long_sig[i] = True
                stop[i] = min(low[i], fibs[2]) * (1 - 1e-4)
                risk = max(close[i] - stop[i], close[i] * 1e-4)
                target[i] = close[i] + 2.0 * risk
                armed_long = False

        if armed_short and not np.isnan(leg_lo) and not np.isnan(leg_hi) and leg_hi > leg_lo:
            span = leg_hi - leg_lo
            fibs = (leg_lo + 0.236 * span, leg_lo + 0.382 * span, leg_lo + 0.50 * span)
            touched = any(low[i] <= f <= high[i] for f in fibs)
            zone = max(fibs)
            reject = touched and (close[i] < open_safe(out, i)) and (close[i] <= zone)
            if reject:
                short_sig[i] = True
                stop[i] = max(high[i], fibs[2]) * (1 + 1e-4)
                risk = max(stop[i] - close[i], close[i] * 1e-4)
                target[i] = close[i] - 2.0 * risk
                armed_short = False

    out["long_signal"] = long_sig
    out["short_signal"] = short_sig
    out["stop_price"] = stop
    out["target_price"] = target
    return out


def open_safe(df: pd.DataFrame, i: int) -> float:
    return float(df["open"].iloc[i])


def to_tradesim_signals(feat: pd.DataFrame, symbol: str, max_hold_bars: int = 64) -> list[Signal]:
    signals: list[Signal] = []
    ts = feat["ts_ms"].to_numpy(np.int64)
    for i in range(len(feat)):
        if feat["long_signal"].iloc[i] and not feat["short_signal"].iloc[i]:
            side = 1
        elif feat["short_signal"].iloc[i] and not feat["long_signal"].iloc[i]:
            side = -1
        else:
            continue
        sp = float(feat["stop_price"].iloc[i])
        tp = float(feat["target_price"].iloc[i])
        if np.isnan(sp) or np.isnan(tp):
            continue
        signals.append(
            Signal(
                ts_ms=int(ts[i]),
                side=side,
                symbol=symbol,
                stop_price=sp,
                target_price=tp,
                max_hold_bars=max_hold_bars,
                tag="tsm_rsi_fib",
            )
        )
    return signals
