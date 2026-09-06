"""Turtle Trading System H0 (Ssmurf gg / dk9c7jC3VO4) — single unit, no pyramid."""

from __future__ import annotations

import numpy as np
import pandas as pd

from strategies.common.signal_sides import SideMode
from tradesim import Signal

STRATEGY_ID = "turtle_donchian_breakout"
STRATEGY_VERSION = "0.1.0"

# System 1 defaults from public Turtle rules (channel exit / pyramid not in H0).
SYS1_ENTRY = 20
SYS1_ATR_STOP = 2.0
ATR_N = 20
WARMUP = SYS1_ENTRY + ATR_N + 2


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
    prior_hi = pd.Series(h).rolling(SYS1_ENTRY, min_periods=SYS1_ENTRY).max().shift(1).to_numpy(float)
    prior_lo = pd.Series(low).rolling(SYS1_ENTRY, min_periods=SYS1_ENTRY).min().shift(1).to_numpy(float)
    atr = _atr(h, low, c, ATR_N)
    long_raw = c > prior_hi
    short_raw = c < prior_lo
    long_raw[:WARMUP] = False
    short_raw[:WARMUP] = False
    both = long_raw & short_raw
    long_raw[both] = short_raw[both] = False
    stop = np.full(len(out), np.nan)
    stop[long_raw] = c[long_raw] - SYS1_ATR_STOP * atr[long_raw]
    stop[short_raw] = c[short_raw] + SYS1_ATR_STOP * atr[short_raw]
    out["donch_hi"] = prior_hi
    out["donch_lo"] = prior_lo
    out["atr"] = atr
    out["long_signal"] = long_raw
    out["short_signal"] = short_raw
    out["stop_price"] = stop
    out["target_price"] = np.nan
    return out


def to_tradesim_signals(
    feat: pd.DataFrame,
    symbol: str,
    max_hold_bars: int = 120,
    *,
    side_mode: SideMode = "long",
) -> list[Signal]:
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
        if use_long and long_sig[i] and np.isfinite(sp) and sp < p:
            sigs.append(
                Signal(
                    ts_ms=int(ts[i]),
                    side=1,
                    symbol=symbol,
                    stop_price=sp,
                    target_price=None,
                    max_hold_bars=max_hold_bars,
                    tag="turtle_s1_long",
                )
            )
        elif use_short and short_sig[i] and np.isfinite(sp) and sp > p:
            sigs.append(
                Signal(
                    ts_ms=int(ts[i]),
                    side=-1,
                    symbol=symbol,
                    stop_price=sp,
                    target_price=None,
                    max_hold_bars=max_hold_bars,
                    tag="turtle_s1_short",
                )
            )
    return sigs
