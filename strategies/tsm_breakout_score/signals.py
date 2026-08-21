"""Causal breakout scorecard signals (path-dependent arming)."""

from __future__ import annotations

import numpy as np
import pandas as pd

from tradesim import Signal

STRATEGY_ID = "tsm_breakout_score"
STRATEGY_VERSION = "0.1.0"


def ema(x: np.ndarray, n: int) -> np.ndarray:
    return pd.Series(x).ewm(span=n, adjust=False).mean().to_numpy(float)


def atr(h, l, c, n=14) -> np.ndarray:
    hs, ls, cs = pd.Series(h), pd.Series(l), pd.Series(c)
    tr = pd.concat([(hs - ls), (hs - cs.shift()).abs(), (ls - cs.shift()).abs()], axis=1).max(axis=1)
    return tr.ewm(alpha=1 / n, adjust=False, min_periods=n).mean().to_numpy(float)


def build_signal_frame(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy().reset_index(drop=True)
    o = out["open"].to_numpy(float)
    h = out["high"].to_numpy(float)
    l = out["low"].to_numpy(float)
    c = out["close"].to_numpy(float)
    vol = out["volume"].to_numpy(float) if "volume" in out.columns else np.ones(len(out))
    n = len(out)
    e50 = ema(c, 50)
    a14 = atr(h, l, c, 14)
    vol_sma = pd.Series(vol).rolling(20, min_periods=20).mean().to_numpy(float)
    roll_hi = pd.Series(h).rolling(20, min_periods=20).max().shift(1).to_numpy(float)
    roll_lo = pd.Series(l).rolling(20, min_periods=20).min().shift(1).to_numpy(float)
    # build-up width ending at i-1
    width8 = pd.Series(h).rolling(8, min_periods=8).max().to_numpy(float) - pd.Series(l).rolling(
        8, min_periods=8
    ).min().to_numpy(float)

    long_sig = np.zeros(n, dtype=bool)
    short_sig = np.zeros(n, dtype=bool)
    stop = np.full(n, np.nan)
    target = np.full(n, np.nan)

    # state machine
    # 0 idle, 1 long_break_armed, 2 long_retested, same for short with negative
    state = 0
    level = np.nan
    break_i = -1
    retest_extreme = np.nan

    for i in range(25, n):
        rng = h[i] - l[i]
        if state == 0:
            # long break candidate
            if (
                np.isfinite(roll_hi[i])
                and c[i] > roll_hi[i]
                and c[i] > e50[i]
                and width8[i - 1] < 1.0 * a14[i]
                and rng > 0
                and (c[i] - l[i]) / rng >= 0.60
                and vol[i] > 1.2 * vol_sma[i]
            ):
                state = 1
                level = float(roll_hi[i])
                break_i = i
                retest_extreme = l[i]
            elif (
                np.isfinite(roll_lo[i])
                and c[i] < roll_lo[i]
                and c[i] < e50[i]
                and width8[i - 1] < 1.0 * a14[i]
                and rng > 0
                and (h[i] - c[i]) / rng >= 0.60
                and vol[i] > 1.2 * vol_sma[i]
            ):
                state = -1
                level = float(roll_lo[i])
                break_i = i
                retest_extreme = h[i]
            continue

        if state == 1:
            if i > break_i + 8:
                state = 0
                continue
            retest_extreme = min(retest_extreme, l[i])
            # Retest hold = entry (follow-through folded into same closed bar)
            if l[i] <= level <= h[i] and c[i] > level and c[i] > o[i] and c[i] > e50[i]:
                long_sig[i] = True
                stop[i] = retest_extreme * (1 - 1e-4)
                risk = max(c[i] - stop[i], c[i] * 1e-4)
                target[i] = c[i] + 2.0 * risk
                state = 0
        elif state == -1:
            if i > break_i + 8:
                state = 0
                continue
            retest_extreme = max(retest_extreme, h[i])
            if l[i] <= level <= h[i] and c[i] < level and c[i] < o[i] and c[i] < e50[i]:
                short_sig[i] = True
                stop[i] = retest_extreme * (1 + 1e-4)
                risk = max(stop[i] - c[i], c[i] * 1e-4)
                target[i] = c[i] - 2.0 * risk
                state = 0

    out["ema50"] = e50
    out["long_signal"] = long_sig
    out["short_signal"] = short_sig
    out["stop_price"] = stop
    out["target_price"] = target
    return out


def to_tradesim_signals(feat: pd.DataFrame, symbol: str, max_hold_bars: int = 48) -> list[Signal]:
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
                    tag="tsm_breakout_score",
                )
            )
    return sigs
