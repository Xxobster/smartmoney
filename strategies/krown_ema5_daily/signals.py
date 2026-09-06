"""Krown 5 Exponential Moving Average daily overlay — vectorized, causal.

Fair H0 from Krown `C0wM-iKfwaI`:
- Daily Bitcoin close above 5 Exponential Moving Average (EMA) → long
- Close below 5 EMA → exit that long (no hard stop in the video)
- Tradesim cannot trail a live EMA exit, so H0 uses a stop at the signal-bar EMA
  plus max_hold (incomplete vs the overlay)
- Long-only source; short_mirror is the inverse cross

Pre-registered improvement (frozen before any look at our results), from his
'paper cut' comment — not a day-of-week search (he already mined that on screen):
enter only if |close − EMA5| > 0.25 × Average True Range (ATR) 14.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from strategies.common.signal_sides import SideMode
from tradesim import Signal

STRATEGY_ID = "krown_ema5_daily"
STRATEGY_VERSION = "0.1.0"

EMA_N = 5
ATR_N = 14
PAPER_CUT_ATR = 0.25
WARMUP = EMA_N + ATR_N + 2


def _atr(high: np.ndarray, low: np.ndarray, close: np.ndarray, n: int) -> np.ndarray:
    prev_c = np.roll(close, 1)
    prev_c[0] = close[0]
    tr = np.maximum(high - low, np.maximum(np.abs(high - prev_c), np.abs(low - prev_c)))
    return pd.Series(tr).ewm(alpha=1.0 / n, adjust=False, min_periods=n).mean().to_numpy(float)


def _build(df: pd.DataFrame, *, paper_cut_atr: float) -> pd.DataFrame:
    out = df.sort_values("ts_ms").reset_index(drop=True).copy()
    h = out["high"].to_numpy(float)
    low = out["low"].to_numpy(float)
    c = out["close"].to_numpy(float)
    ema = pd.Series(c).ewm(span=EMA_N, adjust=False, min_periods=EMA_N).mean().to_numpy(float)
    atr = _atr(h, low, c, ATR_N)
    prev_c = np.roll(c, 1)
    prev_e = np.roll(ema, 1)
    prev_c[0] = prev_e[0] = np.nan
    long_raw = (c > ema) & (prev_c <= prev_e)
    short_raw = (c < ema) & (prev_c >= prev_e)
    if paper_cut_atr > 0.0:
        dist = np.abs(c - ema)
        thick = dist > (paper_cut_atr * atr)
        long_raw = long_raw & thick
        short_raw = short_raw & thick
    long_raw[:WARMUP] = short_raw[:WARMUP] = False
    both = long_raw & short_raw
    long_raw[both] = short_raw[both] = False
    stop = np.full(len(out), np.nan)
    stop[long_raw] = ema[long_raw]
    stop[short_raw] = ema[short_raw]
    out["ema5"] = ema
    out["atr14"] = atr
    out["long_signal"] = long_raw
    out["short_signal"] = short_raw
    out["stop_price"] = stop
    return out


def build_signal_frame(df: pd.DataFrame) -> pd.DataFrame:
    return _build(df, paper_cut_atr=0.0)


def build_signal_frame_papercut(df: pd.DataFrame) -> pd.DataFrame:
    """Pre-registered H0b: skip tiny EMA crosses (paper cuts)."""
    return _build(df, paper_cut_atr=PAPER_CUT_ATR)


def to_tradesim_signals(
    feat: pd.DataFrame,
    symbol: str,
    max_hold_bars: int = 40,
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
                    tag="k5_l",
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
                    tag="k5_s",
                )
            )
    return sigs
