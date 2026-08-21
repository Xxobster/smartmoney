"""Failed breakout / stop-hunt trap signals (path-dependent)."""

from __future__ import annotations

import numpy as np
import pandas as pd

from tradesim import Signal

STRATEGY_ID = "tsm_failed_breakout"
STRATEGY_VERSION = "0.1.0"


def build_signal_frame(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy().reset_index(drop=True)
    o = out["open"].to_numpy(float)
    h = out["high"].to_numpy(float)
    l = out["low"].to_numpy(float)
    c = out["close"].to_numpy(float)
    vol = out["volume"].to_numpy(float) if "volume" in out.columns else np.ones(len(out))
    n = len(out)
    roll_hi = pd.Series(h).rolling(20, min_periods=20).max().shift(1).to_numpy(float)
    roll_lo = pd.Series(l).rolling(20, min_periods=20).min().shift(1).to_numpy(float)
    vol_sma = pd.Series(vol).rolling(20, min_periods=20).mean().to_numpy(float)

    long_sig = np.zeros(n, dtype=bool)
    short_sig = np.zeros(n, dtype=bool)
    stop = np.full(n, np.nan)
    target = np.full(n, np.nan)

    # state: 0 idle; 1 upside sweep pending fail; -1 downside sweep pending fail
    state = 0
    sweep_extreme = np.nan
    sweep_i = -1
    level = np.nan

    for i in range(21, n):
        if state == 0:
            if np.isfinite(roll_hi[i]) and c[i] > roll_hi[i] and vol[i] > vol_sma[i]:
                state = 1
                level = float(roll_hi[i])
                sweep_extreme = h[i]
                sweep_i = i
            elif np.isfinite(roll_lo[i]) and c[i] < roll_lo[i] and vol[i] > vol_sma[i]:
                state = -1
                level = float(roll_lo[i])
                sweep_extreme = l[i]
                sweep_i = i
            continue

        if state == 1:
            sweep_extreme = max(sweep_extreme, h[i])
            if i > sweep_i + 3:
                state = 0
                continue
            if c[i] < level and c[i] < o[i]:
                short_sig[i] = True
                stop[i] = sweep_extreme * (1 + 1e-4)
                risk = max(stop[i] - c[i], c[i] * 1e-4)
                target[i] = c[i] - 2.0 * risk
                state = 0
        elif state == -1:
            sweep_extreme = min(sweep_extreme, l[i])
            if i > sweep_i + 3:
                state = 0
                continue
            if c[i] > level and c[i] > o[i]:
                long_sig[i] = True
                stop[i] = sweep_extreme * (1 - 1e-4)
                risk = max(c[i] - stop[i], c[i] * 1e-4)
                target[i] = c[i] + 2.0 * risk
                state = 0

    out["long_signal"] = long_sig
    out["short_signal"] = short_sig
    out["stop_price"] = stop
    out["target_price"] = target
    return out


def to_tradesim_signals(feat: pd.DataFrame, symbol: str, max_hold_bars: int = 32) -> list[Signal]:
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
                    tag="tsm_fail_bo",
                )
            )
    return sigs
