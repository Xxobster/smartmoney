"""HalfTrend + Exponential Moving Average 60 + ATR 1.5/3. Vectorized except HalfTrend pass."""

from __future__ import annotations

import numpy as np
import pandas as pd

from strategies.common.halftrend import halftrend_trend
from strategies.common.signal_sides import SideMode
from tradesim import Signal

STRATEGY_ID = "halftrend_ema_atr"
STRATEGY_VERSION = "0.1.0"

HT_AMP = 2
HT_DEV = 2.0
HT_ATR = 100
EMA_N = 60
ATR_N = 14
STOP_K = 1.5
TP_K = 3.0
WARMUP = EMA_N + ATR_N + HT_AMP + 2


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
    ht = halftrend_trend(h, low, c, amplitude=HT_AMP, channel_deviation=HT_DEV, atr_n=HT_ATR)
    prev_ht = np.roll(ht, 1)
    prev_ht[0] = ht[0]
    ema = pd.Series(c).ewm(span=EMA_N, adjust=False, min_periods=EMA_N).mean().to_numpy(float)
    atr = _atr(h, low, c, ATR_N)
    blue = (ht == 0) & (prev_ht == 1)
    red = (ht == 1) & (prev_ht == 0)
    long_raw = blue & (c > ema)
    short_raw = red & (c < ema)
    long_raw[0] = short_raw[0] = False
    long_raw[:WARMUP] = short_raw[:WARMUP] = False
    both = long_raw & short_raw
    long_raw[both] = short_raw[both] = False
    stop = np.full(len(out), np.nan)
    target = np.full(len(out), np.nan)
    stop[long_raw] = c[long_raw] - STOP_K * atr[long_raw]
    target[long_raw] = c[long_raw] + TP_K * atr[long_raw]
    stop[short_raw] = c[short_raw] + STOP_K * atr[short_raw]
    target[short_raw] = c[short_raw] - TP_K * atr[short_raw]
    out["ht_trend"] = ht
    out["ema60"] = ema
    out["atr14"] = atr
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
                    tag="ht_l",
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
                    tag="ht_s",
                )
            )
    return sigs
