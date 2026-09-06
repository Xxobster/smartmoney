"""Multi-timeframe EMA pullback — vectorized, causal 4h filter on 1h bars.

Fair H0 (public rules, simplified):
- 4h: price above/below 200 EMA; EMA slope vs 5 completed 4h bars prior
- 1h: pullback touch 20 EMA; bullish/bearish close; volume > prior bar
- Stop: 1.2 * ATR(14) from signal close
- Take-profit: full position at 1R (50% + EMA trail omitted in tradesim)
- CPI/FOMC / compressed ATR / range-bound filters omitted
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from engine.features import lag_htf_to_ltf
from strategies.common.signal_sides import SideMode
from tradesim import Signal

STRATEGY_ID = "quant_forge_mtf_ema_pullback"
STRATEGY_VERSION = "0.1.0"

EMA_LTF = 20
EMA_HTF = 200
ATR_N = 14
ATR_STOP_MULT = 1.2
SLOPE_LOOKBACK = 5
WARMUP = EMA_HTF * 4 + EMA_LTF + ATR_N + SLOPE_LOOKBACK + 10


def _ema(x: np.ndarray, n: int) -> np.ndarray:
    return pd.Series(x).ewm(span=n, adjust=False, min_periods=n).mean().to_numpy(float)


def _atr(high: np.ndarray, low: np.ndarray, close: np.ndarray, n: int) -> np.ndarray:
    prev_c = np.roll(close, 1)
    prev_c[0] = close[0]
    tr = np.maximum(high - low, np.maximum(np.abs(high - prev_c), np.abs(low - prev_c)))
    return pd.Series(tr).ewm(alpha=1.0 / n, adjust=False, min_periods=n).mean().to_numpy(float)


def _four_hour_from_one_hour(df: pd.DataFrame) -> pd.DataFrame:
    x = df.sort_values("ts_ms").copy()
    idx = pd.to_datetime(x["ts_ms"], unit="ms", utc=True)
    g = x.set_index(idx)
    r = g.resample("4h", label="left", closed="left").agg(
        {"open": "first", "high": "max", "low": "min", "close": "last", "volume": "sum"}
    )
    r = r.dropna(subset=["close"]).copy()
    r["ts_ms"] = np.array([int(t.timestamp() * 1000) for t in r.index], dtype=np.int64)
    return r.reset_index(drop=True)


def build_signal_frame(df: pd.DataFrame) -> pd.DataFrame:
    out = df.sort_values("ts_ms").reset_index(drop=True).copy()
    c = out["close"].to_numpy(float)
    h = out["high"].to_numpy(float)
    low = out["low"].to_numpy(float)
    o = out["open"].to_numpy(float)
    vol = out["volume"].to_numpy(float)

    ema20 = _ema(c, EMA_LTF)
    atr = _atr(h, low, c, ATR_N)
    vol_up = vol > np.roll(vol, 1)
    vol_up[0] = False
    bull = c > o
    bear = c < o

    htf = _four_hour_from_one_hour(out)
    htf_c = htf["close"].to_numpy(float)
    htf_ema = _ema(htf_c, EMA_HTF)
    slope_up = htf_ema > np.roll(htf_ema, SLOPE_LOOKBACK)
    slope_dn = htf_ema < np.roll(htf_ema, SLOPE_LOOKBACK)
    slope_up[:EMA_HTF + SLOPE_LOOKBACK] = False
    slope_dn[:EMA_HTF + SLOPE_LOOKBACK] = False
    above = htf_c > htf_ema
    below = htf_c < htf_ema

    htf_feat = pd.DataFrame(
        {
            "ts_ms": htf["ts_ms"].to_numpy(np.int64),
            "ema200": htf_ema,
            "slope_up": slope_up,
            "slope_down": slope_dn,
            "above_ema": above,
            "below_ema": below,
        }
    )
    aligned = lag_htf_to_ltf(out, htf_feat, "4h")
    htf_above = aligned["htf_above_ema"].to_numpy(bool)
    htf_below = aligned["htf_below_ema"].to_numpy(bool)
    htf_slope_up = aligned["htf_slope_up"].to_numpy(bool)
    htf_slope_dn = aligned["htf_slope_down"].to_numpy(bool)

    touch_ema = (low <= ema20) & (h >= ema20)
    long_raw = htf_above & htf_slope_up & touch_ema & bull & vol_up & (c >= ema20)
    short_raw = htf_below & htf_slope_dn & touch_ema & bear & vol_up & (c <= ema20)
    both = long_raw & short_raw
    long_raw[both] = short_raw[both] = False
    long_raw[:WARMUP] = short_raw[:WARMUP] = False

    stop = np.full(len(out), np.nan)
    target = np.full(len(out), np.nan)
    stop[long_raw] = c[long_raw] - ATR_STOP_MULT * atr[long_raw]
    target[long_raw] = c[long_raw] + (c[long_raw] - stop[long_raw])
    stop[short_raw] = c[short_raw] + ATR_STOP_MULT * atr[short_raw]
    target[short_raw] = c[short_raw] - (stop[short_raw] - c[short_raw])

    out["ema20"] = ema20
    out["atr14"] = atr
    out["long_signal"] = long_raw
    out["short_signal"] = short_raw
    out["stop_price"] = stop
    out["target_price"] = target
    return out


def to_tradesim_signals(
    feat: pd.DataFrame,
    symbol: str,
    max_hold_bars: int = 72,
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
                    tag="qf_mtf_l",
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
                    tag="qf_mtf_s",
                )
            )
    return sigs
