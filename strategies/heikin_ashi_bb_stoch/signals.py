"""Heikin Ashi × Bollinger × Stochastic RSI H0 — vectorized, causal.

Fair H0 from Crypto_Fox `qP2XkQcr2eU` (public description):
- Trend: EMA 40 vs SMA 50
- Bollinger 20, 2σ (length not stated; fair default)
- Stochastic RSI: RSI 13, stoch 10, K/D 3, 20/80
- Long: EMA>SMA, lower-band touch in last 5 bars with stoch<20, close back inside,
  stoch rising, Heikin Ashi flips green (mirror short)
- Stop: extreme of last touch candle; take-profit 1R (HA-color exit omitted)
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from strategies.common.signal_sides import SideMode
from tradesim import Signal

STRATEGY_ID = "heikin_ashi_bb_stoch"
STRATEGY_VERSION = "0.1.0"

EMA_N = 40
SMA_N = 50
BB_N = 20
BB_K = 2.0
RSI_N = 13
STOCH_N = 10
SMOOTH_K = 3
SMOOTH_D = 3
STOCH_OS = 20.0
STOCH_OB = 80.0
TOUCH_LOOKBACK = 5
WARMUP = SMA_N + BB_N + RSI_N + STOCH_N + SMOOTH_K + SMOOTH_D + TOUCH_LOOKBACK + 2


def _ema(x: np.ndarray, n: int) -> np.ndarray:
    return pd.Series(x).ewm(span=n, adjust=False, min_periods=n).mean().to_numpy(float)


def _sma(x: np.ndarray, n: int) -> np.ndarray:
    return pd.Series(x).rolling(n, min_periods=n).mean().to_numpy(float)


def _rsi(close: np.ndarray, n: int) -> np.ndarray:
    d = np.diff(close, prepend=close[0])
    up = np.where(d > 0.0, d, 0.0)
    dn = np.where(d < 0.0, -d, 0.0)
    ru = pd.Series(up).ewm(alpha=1.0 / n, adjust=False, min_periods=n).mean()
    rd = pd.Series(dn).ewm(alpha=1.0 / n, adjust=False, min_periods=n).mean()
    return (100.0 - 100.0 / (1.0 + ru / (rd + 1e-12))).to_numpy(float)


def _stoch_rsi(close: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    rsi = _rsi(close, RSI_N)
    s = pd.Series(rsi)
    lo = s.rolling(STOCH_N, min_periods=STOCH_N).min()
    hi = s.rolling(STOCH_N, min_periods=STOCH_N).max()
    raw = 100.0 * (s - lo) / (hi - lo + 1e-12)
    k = raw.rolling(SMOOTH_K, min_periods=SMOOTH_K).mean()
    d = k.rolling(SMOOTH_D, min_periods=SMOOTH_D).mean()
    return k.to_numpy(float), d.to_numpy(float)


def _heikin_ashi(
    o: np.ndarray, h: np.ndarray, low: np.ndarray, c: np.ndarray
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    ha_c = (o + h + low + c) / 4.0
    x = np.empty_like(ha_c)
    x[0] = 0.5 * (o[0] + c[0])
    if len(ha_c) > 1:
        x[1:] = ha_c[:-1]
    ha_o = pd.Series(x).ewm(alpha=0.5, adjust=False).mean().to_numpy(float)
    ha_h = np.maximum(h, np.maximum(ha_o, ha_c))
    ha_l = np.minimum(low, np.minimum(ha_o, ha_c))
    return ha_o, ha_h, ha_l, ha_c


def build_signal_frame(df: pd.DataFrame) -> pd.DataFrame:
    out = df.sort_values("ts_ms").reset_index(drop=True).copy()
    o = out["open"].to_numpy(float)
    h = out["high"].to_numpy(float)
    low = out["low"].to_numpy(float)
    c = out["close"].to_numpy(float)
    ema40 = _ema(c, EMA_N)
    sma50 = _sma(c, SMA_N)
    mid = pd.Series(c).rolling(BB_N, min_periods=BB_N).mean()
    std = pd.Series(c).rolling(BB_N, min_periods=BB_N).std(ddof=1)
    bb_u = (mid + BB_K * std).to_numpy(float)
    bb_l = (mid - BB_K * std).to_numpy(float)
    stoch_k, stoch_d = _stoch_rsi(c)
    ha_o, ha_h, ha_l, ha_c = _heikin_ashi(o, h, low, c)
    ha_green = ha_c > ha_o
    ha_red = ha_c < ha_o
    prev_green = np.roll(ha_green, 1)
    prev_red = np.roll(ha_red, 1)
    prev_green[0] = prev_red[0] = False
    ha_flip_green = ha_green & prev_red
    ha_flip_red = ha_red & prev_green
    stoch_up = stoch_k > np.roll(stoch_k, 1)
    stoch_dn = stoch_k < np.roll(stoch_k, 1)
    stoch_up[0] = stoch_dn[0] = False
    touch_low = (low <= bb_l) & (stoch_k < STOCH_OS)
    touch_high = (h >= bb_u) & (stoch_k > STOCH_OB)
    idx = np.arange(len(out), dtype=float)
    last_low_i = pd.Series(np.where(touch_low, idx, np.nan)).ffill().to_numpy(float)
    last_high_i = pd.Series(np.where(touch_high, idx, np.nan)).ffill().to_numpy(float)
    last_touch_low = pd.Series(np.where(touch_low, low, np.nan)).ffill().to_numpy(float)
    last_touch_high = pd.Series(np.where(touch_high, h, np.nan)).ffill().to_numpy(float)
    low_age_ok = (idx - last_low_i) <= TOUCH_LOOKBACK
    high_age_ok = (idx - last_high_i) <= TOUCH_LOOKBACK
    reclaim_low = c > bb_l
    reclaim_high = c < bb_u
    trend_up = ema40 > sma50
    trend_dn = ema40 < sma50
    long_raw = trend_up & low_age_ok & reclaim_low & stoch_up & ha_flip_green
    short_raw = trend_dn & high_age_ok & reclaim_high & stoch_dn & ha_flip_red
    both = long_raw & short_raw
    long_raw[both] = short_raw[both] = False
    long_raw[:WARMUP] = short_raw[:WARMUP] = False
    stop = np.full(len(out), np.nan)
    target = np.full(len(out), np.nan)
    stop[long_raw] = last_touch_low[long_raw]
    target[long_raw] = c[long_raw] + (c[long_raw] - stop[long_raw])
    stop[short_raw] = last_touch_high[short_raw]
    target[short_raw] = c[short_raw] - (stop[short_raw] - c[short_raw])
    out["ema40"] = ema40
    out["sma50"] = sma50
    out["bb_upper"] = bb_u
    out["bb_lower"] = bb_l
    out["stoch_k"] = stoch_k
    out["stoch_d"] = stoch_d
    out["ha_open"] = ha_o
    out["ha_close"] = ha_c
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
            if not np.isfinite(sp) or not np.isfinite(tp) or not (sp < p < tp):
                continue
            sigs.append(
                Signal(
                    ts_ms=int(ts[i]),
                    side=1,
                    symbol=symbol,
                    stop_price=sp,
                    target_price=tp,
                    max_hold_bars=max_hold_bars,
                    tag="ha_bb_l",
                )
            )
        elif use_short and short_sig[i]:
            if not np.isfinite(sp) or not np.isfinite(tp) or not (tp < p < sp):
                continue
            sigs.append(
                Signal(
                    ts_ms=int(ts[i]),
                    side=-1,
                    symbol=symbol,
                    stop_price=sp,
                    target_price=tp,
                    max_hold_bars=max_hold_bars,
                    tag="ha_bb_s",
                )
            )
    return sigs
