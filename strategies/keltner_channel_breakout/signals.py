"""Keltner Channel long-only breakout H0 — vectorized; sides via side_mode.

Fair defaults (not creator heatmap optima): EMA length 20, ATR length 20,
ATR multiplier 2. Video exit is close below middle; tradesim has no dynamic
mid-band exit, so H0 uses a causal stop at the middle band on the signal bar
plus a safety max_hold.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from strategies.common.signal_sides import SideMode
from tradesim import Signal

STRATEGY_ID = "keltner_channel_breakout"
STRATEGY_VERSION = "0.1.0"

EMA_N = 20
ATR_N = 20
ATR_MULT = 2.0
WARMUP = max(EMA_N, ATR_N) + 2


def _atr(high: np.ndarray, low: np.ndarray, close: np.ndarray, n: int) -> np.ndarray:
    prev_c = np.roll(close, 1)
    prev_c[0] = close[0]
    tr = np.maximum(high - low, np.maximum(np.abs(high - prev_c), np.abs(low - prev_c)))
    return pd.Series(tr).ewm(alpha=1.0 / n, adjust=False, min_periods=n).mean().to_numpy(float)


def build_signal_frame(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy().reset_index(drop=True)
    h = out["high"].to_numpy(float)
    low = out["low"].to_numpy(float)
    c = out["close"].to_numpy(float)
    mid = pd.Series(c).ewm(span=EMA_N, adjust=False, min_periods=EMA_N).mean().to_numpy(float)
    atr = _atr(h, low, c, ATR_N)
    upper = mid + ATR_MULT * atr
    lower = mid - ATR_MULT * atr
    prev_c = np.roll(c, 1)
    prev_u = np.roll(upper, 1)
    prev_l = np.roll(lower, 1)
    prev_c[0] = prev_u[0] = prev_l[0] = np.nan
    long_raw = (c > upper) & (prev_c <= prev_u)
    short_raw = (c < lower) & (prev_c >= prev_l)
    long_raw[:WARMUP] = False
    short_raw[:WARMUP] = False
    out["kc_mid"] = mid
    out["kc_upper"] = upper
    out["kc_lower"] = lower
    out["kc_atr"] = atr
    out["long_signal"] = long_raw
    out["short_signal"] = short_raw
    stop = np.full(len(out), np.nan)
    stop[long_raw] = mid[long_raw]
    stop[short_raw] = mid[short_raw]
    out["stop_price"] = stop
    out["target_price"] = np.nan
    return out


def to_tradesim_signals(
    feat: pd.DataFrame,
    symbol: str,
    max_hold_bars: int = 96,
    *,
    side_mode: SideMode = "long",
) -> list[Signal]:
    """Emit entry signals for the requested side_mode (report sides separately)."""
    sigs: list[Signal] = []
    ts = feat["ts_ms"].to_numpy(np.int64)
    long_sig = feat["long_signal"].to_numpy(bool)
    short_sig = feat["short_signal"].to_numpy(bool)
    stop = feat["stop_price"].to_numpy(float)
    px = feat["close"].to_numpy(float)

    use_long = side_mode in ("long", "long_mirror")
    use_short = side_mode in ("short", "short_mirror")

    for i in range(len(feat)):
        p = float(px[i])
        sp = float(stop[i])
        if use_long and long_sig[i]:
            if not np.isfinite(sp) or not (sp < p):
                continue
            sigs.append(
                Signal(
                    ts_ms=int(ts[i]),
                    side=1,
                    symbol=symbol,
                    stop_price=sp,
                    target_price=None,
                    max_hold_bars=max_hold_bars,
                    tag="kc_long" if side_mode == "long" else "kc_long_mirror",
                )
            )
        elif use_short and short_sig[i]:
            if not np.isfinite(sp) or not (sp > p):
                continue
            sigs.append(
                Signal(
                    ts_ms=int(ts[i]),
                    side=-1,
                    symbol=symbol,
                    stop_price=sp,
                    target_price=None,
                    max_hold_bars=max_hold_bars,
                    tag="kc_short_mirror" if side_mode == "short_mirror" else "kc_short",
                )
            )
    return sigs
