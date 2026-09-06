"""Double Bollinger 20 ± 0.5 inner-range, then prior-bar break. Vectorized.

Crypto_Fox `0cn9mAnOoX0` breakout method. Ranging = prior close inside 0.5 bands.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from strategies.common.signal_sides import SideMode
from tradesim import Signal

STRATEGY_ID = "double_bb_range_break"
STRATEGY_VERSION = "0.1.0"

BB_N = 20
INNER_K = 0.5
RR = 1.5
WARMUP = BB_N + 2


def build_signal_frame(df: pd.DataFrame) -> pd.DataFrame:
    out = df.sort_values("ts_ms").reset_index(drop=True).copy()
    h = out["high"].to_numpy(float)
    low = out["low"].to_numpy(float)
    c = out["close"].to_numpy(float)
    mid = pd.Series(c).rolling(BB_N, min_periods=BB_N).mean().to_numpy(float)
    std = pd.Series(c).rolling(BB_N, min_periods=BB_N).std(ddof=0).to_numpy(float)
    inner_up = mid + INNER_K * std
    inner_dn = mid - INNER_K * std
    prev_c = np.roll(c, 1)
    prev_h = np.roll(h, 1)
    prev_l = np.roll(low, 1)
    prev_up = np.roll(inner_up, 1)
    prev_dn = np.roll(inner_dn, 1)
    prev_c[0] = prev_h[0] = prev_l[0] = prev_up[0] = prev_dn[0] = np.nan
    ranging = (prev_c >= prev_dn) & (prev_c <= prev_up)
    long_raw = ranging & (c > prev_h)
    short_raw = ranging & (c < prev_l)
    long_raw[:WARMUP] = False
    short_raw[:WARMUP] = False
    both = long_raw & short_raw
    long_raw[both] = short_raw[both] = False
    stop = np.full(len(out), np.nan)
    target = np.full(len(out), np.nan)
    stop[long_raw] = inner_dn[long_raw]
    risk_l = c[long_raw] - inner_dn[long_raw]
    target[long_raw] = c[long_raw] + RR * risk_l
    stop[short_raw] = inner_up[short_raw]
    risk_s = inner_up[short_raw] - c[short_raw]
    target[short_raw] = c[short_raw] - RR * risk_s
    out["bb_mid"] = mid
    out["bb_inner_up"] = inner_up
    out["bb_inner_dn"] = inner_dn
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
                    tag="dbb_l",
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
                    tag="dbb_s",
                )
            )
    return sigs
