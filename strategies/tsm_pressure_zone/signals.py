"""Vectorized pressure-zone signals from overlapping candle shadows (causal H0)."""

from __future__ import annotations

import numpy as np
import pandas as pd

from tradesim import Signal

STRATEGY_ID = "tsm_pressure_zone"
STRATEGY_VERSION = "0.1.0"


def ema(x: np.ndarray, n: int) -> np.ndarray:
    return pd.Series(x).ewm(span=n, adjust=False).mean().to_numpy(float)


def build_signal_frame(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy().reset_index(drop=True)
    o = out["open"].to_numpy(float)
    h = out["high"].to_numpy(float)
    l = out["low"].to_numpy(float)
    c = out["close"].to_numpy(float)
    n = len(out)
    e50 = ema(c, 50)
    out["ema50"] = e50

    body_lo = np.minimum(o, c)
    body_hi = np.maximum(o, c)
    has_lower = l < body_lo
    has_upper = h > body_hi

    long_sig = np.zeros(n, dtype=bool)
    short_sig = np.zeros(n, dtype=bool)
    stop = np.full(n, np.nan)
    target = np.full(n, np.nan)
    zone_top = np.full(n, np.nan)
    zone_bot = np.full(n, np.nan)

    if n < 4:
        out["long_signal"] = long_sig
        out["short_signal"] = short_sig
        out["stop_price"] = stop
        out["target_price"] = target
        out["zone_top"] = zone_top
        out["zone_bot"] = zone_bot
        return out

    # Windows ending at i (bars i-2,i-1,i)
    i0 = np.arange(2, n)
    i1 = i0 - 1
    i2 = i0 - 2

    bull_overlap = (
        has_lower[i0] & has_lower[i1] & has_lower[i2]
        & (np.maximum(np.maximum(l[i0], l[i1]), l[i2]) < np.minimum(np.minimum(body_lo[i0], body_lo[i1]), body_lo[i2]))
    )
    bear_overlap = (
        has_upper[i0] & has_upper[i1] & has_upper[i2]
        & (np.maximum(np.maximum(body_hi[i0], body_hi[i1]), body_hi[i2]) < np.minimum(np.minimum(h[i0], h[i1]), h[i2]))
    )

    b_z_top = np.minimum(np.minimum(c[i0], c[i1]), c[i2])  # lowest close
    b_z_bot = np.minimum(np.minimum(l[i0], l[i1]), l[i2])  # lowest low
    s_z_top = np.maximum(np.maximum(h[i0], h[i1]), h[i2])
    s_z_bot = np.maximum(np.maximum(c[i0], c[i1]), c[i2])  # highest close

    # Third-bar entries
    third_long = (
        bull_overlap
        & (c[i0] > o[i0])
        & (c[i0] > b_z_top)
        & (l[i0] <= b_z_top)
        & (h[i0] >= b_z_bot)
        & (c[i0] > e50[i0])
    )
    third_short = (
        bear_overlap
        & (c[i0] < o[i0])
        & (c[i0] < s_z_bot)
        & (h[i0] >= s_z_bot)
        & (l[i0] <= s_z_top)
        & (c[i0] < e50[i0])
    )

    long_sig[i0[third_long]] = True
    short_sig[i0[third_short]] = True
    stop[i0[third_long]] = b_z_bot[third_long] * (1 - 1e-4)
    zone_top[i0[third_long]] = b_z_top[third_long]
    zone_bot[i0[third_long]] = b_z_bot[third_long]
    stop[i0[third_short]] = s_z_top[third_short] * (1 + 1e-4)
    zone_top[i0[third_short]] = s_z_top[third_short]
    zone_bot[i0[third_short]] = s_z_bot[third_short]

    # Next-bar entries when third bar did not qualify
    # Zone ends at j=i0; signal bar is j+1 = i0+1
    j = i0[:-1]  # zone end indices that have a next bar
    nxt = j + 1
    # Map zone arrays: bull_overlap aligned to i0; for j = i0[:-1], use same mask[:-1]
    bull_z = bull_overlap[:-1]
    bear_z = bear_overlap[:-1]
    no_third_l = ~third_long[:-1]
    no_third_s = ~third_short[:-1]

    next_long = (
        bull_z & no_third_l
        & (c[nxt] > o[nxt])
        & (c[nxt] > b_z_top[:-1])
        & (c[nxt] >= b_z_bot[:-1])  # not invalidated
        & (l[nxt] <= b_z_top[:-1])
        & (h[nxt] >= b_z_bot[:-1])
        & (c[nxt] > e50[nxt])
        & ~long_sig[nxt]
    )
    next_short = (
        bear_z & no_third_s
        & (c[nxt] < o[nxt])
        & (c[nxt] < s_z_bot[:-1])
        & (c[nxt] <= s_z_top[:-1])
        & (h[nxt] >= s_z_bot[:-1])
        & (l[nxt] <= s_z_top[:-1])
        & (c[nxt] < e50[nxt])
        & ~short_sig[nxt]
    )

    long_sig[nxt[next_long]] = True
    short_sig[nxt[next_short]] = True
    stop[nxt[next_long]] = b_z_bot[:-1][next_long] * (1 - 1e-4)
    zone_top[nxt[next_long]] = b_z_top[:-1][next_long]
    zone_bot[nxt[next_long]] = b_z_bot[:-1][next_long]
    stop[nxt[next_short]] = s_z_top[:-1][next_short] * (1 + 1e-4)
    zone_top[nxt[next_short]] = s_z_top[:-1][next_short]
    zone_bot[nxt[next_short]] = s_z_bot[:-1][next_short]

    # Resolve both-side conflict: drop both
    both = long_sig & short_sig
    long_sig[both] = False
    short_sig[both] = False
    stop[both] = np.nan

    risk = np.full(n, np.nan)
    risk[long_sig] = np.maximum(c[long_sig] - stop[long_sig], c[long_sig] * 1e-4)
    target[long_sig] = c[long_sig] + 2.0 * risk[long_sig]
    risk[short_sig] = np.maximum(stop[short_sig] - c[short_sig], c[short_sig] * 1e-4)
    target[short_sig] = c[short_sig] - 2.0 * risk[short_sig]

    # Edge-trigger clusters
    long_e = long_sig & ~np.roll(long_sig, 1)
    short_e = short_sig & ~np.roll(short_sig, 1)
    long_e[0] = short_e[0] = False
    # clear non-edge stops/targets
    drop = (long_sig & ~long_e) | (short_sig & ~short_e)
    stop[drop] = np.nan
    target[drop] = np.nan
    long_sig = long_e
    short_sig = short_e

    out["long_signal"] = long_sig
    out["short_signal"] = short_sig
    out["stop_price"] = stop
    out["target_price"] = target
    out["zone_top"] = zone_top
    out["zone_bot"] = zone_bot
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
                    tag="tsm_pressure_zone",
                )
            )
    return sigs
