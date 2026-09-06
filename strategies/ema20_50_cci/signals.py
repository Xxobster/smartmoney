"""20/50 Exponential Moving Average cross + 200 EMA + Commodity Channel Index H0.

Fair freeze from `RFMM8WkLXVI` (Crypto Trading), stated 30-minute Bitcoin rules,
mapped to 1-hour (closest project research timeframe with 1-minute touch bars):
- Long: EMA 20 crosses above EMA 50; both EMAs above EMA 200; CCI 14 > 100
- Short: EMA 20 crosses below EMA 50; both EMAs below EMA 200; CCI 14 < -100
- Stop = 1 × Average True Range (ATR) 14 at the signal close (he used ATR as distance)
- Take-profit 1.5R
- Session-hour filter omitted (his personal window, not a public rule)
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from strategies.common.signal_sides import SideMode
from tradesim import Signal

STRATEGY_ID = "ema20_50_cci"
STRATEGY_VERSION = "0.1.0"

EMA_FAST = 20
EMA_SLOW = 50
EMA_TREND = 200
CCI_N = 14
CCI_LEVEL = 100.0
ATR_N = 14
ATR_STOP = 1.0
RR = 1.5
WARMUP = EMA_TREND + CCI_N + ATR_N


def _ema(x: np.ndarray, n: int) -> np.ndarray:
    return pd.Series(x).ewm(span=n, adjust=False, min_periods=n).mean().to_numpy(float)


def _atr(high: np.ndarray, low: np.ndarray, close: np.ndarray, n: int) -> np.ndarray:
    prev_c = np.roll(close, 1)
    prev_c[0] = close[0]
    tr = np.maximum(high - low, np.maximum(np.abs(high - prev_c), np.abs(low - prev_c)))
    return pd.Series(tr).ewm(alpha=1.0 / n, adjust=False, min_periods=n).mean().to_numpy(float)


def _cci(high: np.ndarray, low: np.ndarray, close: np.ndarray, n: int) -> np.ndarray:
    tp = (high + low + close) / 3.0
    sma = pd.Series(tp).rolling(n, min_periods=n).mean()
    mad = (pd.Series(tp) - sma).abs().rolling(n, min_periods=n).mean()
    return ((pd.Series(tp) - sma) / (0.015 * mad.replace(0.0, np.nan))).to_numpy(float)


def build_signal_frame(df: pd.DataFrame) -> pd.DataFrame:
    out = df.sort_values("ts_ms").reset_index(drop=True).copy()
    h = out["high"].to_numpy(float)
    low = out["low"].to_numpy(float)
    c = out["close"].to_numpy(float)
    e20 = _ema(c, EMA_FAST)
    e50 = _ema(c, EMA_SLOW)
    e200 = _ema(c, EMA_TREND)
    cci = _cci(h, low, c, CCI_N)
    atr = _atr(h, low, c, ATR_N)
    p20 = np.roll(e20, 1)
    p50 = np.roll(e50, 1)
    p20[0] = p50[0] = np.nan
    long_raw = (e20 > e50) & (p20 <= p50) & (e20 > e200) & (e50 > e200) & (cci > CCI_LEVEL)
    short_raw = (e20 < e50) & (p20 >= p50) & (e20 < e200) & (e50 < e200) & (cci < -CCI_LEVEL)
    both = long_raw & short_raw
    long_raw[both] = short_raw[both] = False
    long_raw[:WARMUP] = short_raw[:WARMUP] = False
    stop = np.full(len(out), np.nan)
    target = np.full(len(out), np.nan)
    stop[long_raw] = c[long_raw] - ATR_STOP * atr[long_raw]
    target[long_raw] = c[long_raw] + RR * ATR_STOP * atr[long_raw]
    stop[short_raw] = c[short_raw] + ATR_STOP * atr[short_raw]
    target[short_raw] = c[short_raw] - RR * ATR_STOP * atr[short_raw]
    out["ema20"] = e20
    out["ema50"] = e50
    out["ema200"] = e200
    out["cci14"] = cci
    out["atr14"] = atr
    out["long_signal"] = long_raw
    out["short_signal"] = short_raw
    out["stop_price"] = stop
    out["target_price"] = target
    return out


def to_tradesim_signals(
    feat: pd.DataFrame,
    symbol: str,
    max_hold_bars: int = 48,
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
                    tag="e20_l",
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
                    tag="e20_s",
                )
            )
    return sigs
