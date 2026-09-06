"""SuperTrend 8×4 + Exponential Moving Average 200, 1.5×ATR stop.

Quant Tactics `53yqW60SDPk`. 4-hour only. Not a chandelier retune.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from strategies.common.signal_sides import SideMode
from strategies.common.supertrend import supertrend_line_dir
from tradesim import Signal

STRATEGY_ID = "quant_tactics_st_ema200"
STRATEGY_VERSION = "0.1.0"

ST_N = 8
ST_K = 4.0
EMA_N = 200
ATR_STOP = 1.5
WARMUP = EMA_N + ST_N + 2


def _atr(high: np.ndarray, low: np.ndarray, close: np.ndarray, n: int) -> np.ndarray:
    prev_c = np.roll(close, 1)
    prev_c[0] = close[0]
    tr = np.maximum(high - low, np.maximum(np.abs(high - prev_c), np.abs(low - prev_c)))
    return pd.Series(tr).ewm(alpha=1.0 / n, adjust=False, min_periods=n).mean().to_numpy(float)


def build_signal_frame(df: pd.DataFrame) -> pd.DataFrame:
    out = df.sort_values("ts_ms").reset_index(drop=True).copy()
    h = out["high"].to_numpy(float)
    low = out["low"].to_numpy(float)
    c = out["close"].to_numpy(float)
    st_line, st_dir = supertrend_line_dir(h, low, c, atr_n=ST_N, multiplier=ST_K)
    ema = pd.Series(c).ewm(span=EMA_N, adjust=False, min_periods=EMA_N).mean().to_numpy(float)
    atr = _atr(h, low, c, ST_N)
    long_on = (c > st_line) & (c > ema) & (st_dir == 1)
    short_on = (c < st_line) & (c < ema) & (st_dir == -1)
    long_raw = long_on & ~np.roll(long_on, 1)
    short_raw = short_on & ~np.roll(short_on, 1)
    long_raw[0] = short_raw[0] = False
    long_raw[:WARMUP] = short_raw[:WARMUP] = False
    both = long_raw & short_raw
    long_raw[both] = short_raw[both] = False
    stop = np.full(len(out), np.nan)
    target = np.full(len(out), np.nan)
    stop[long_raw] = c[long_raw] - ATR_STOP * atr[long_raw]
    stop[short_raw] = c[short_raw] + ATR_STOP * atr[short_raw]
    out["st_line"] = st_line
    out["st_dir"] = st_dir
    out["ema200"] = ema
    out["atr8"] = atr
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
    px = feat["close"].to_numpy(float)
    use_long = side_mode in ("long", "long_mirror")
    use_short = side_mode in ("short", "short_mirror")
    for i in range(len(feat)):
        p = float(px[i])
        sp = float(stop[i])
        if use_long and long_sig[i]:
            if not (np.isfinite(sp) and sp < p):
                continue
            sigs.append(
                Signal(
                    ts_ms=int(ts[i]),
                    side=1,
                    symbol=symbol,
                    stop_price=sp,
                    target_price=None,
                    max_hold_bars=max_hold_bars,
                    tag="st200_l",
                )
            )
        elif use_short and short_sig[i]:
            if not (np.isfinite(sp) and sp > p):
                continue
            sigs.append(
                Signal(
                    ts_ms=int(ts[i]),
                    side=-1,
                    symbol=symbol,
                    stop_price=sp,
                    target_price=None,
                    max_hold_bars=max_hold_bars,
                    tag="st200_s",
                )
            )
    return sigs
