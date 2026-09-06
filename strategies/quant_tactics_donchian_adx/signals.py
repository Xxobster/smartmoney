"""Donchian + ADX + Choppiness H0 — vectorized, causal prior-channel.

Fair H0 from Quant Tactics `CgYdfwrL1VQ`:
- ETH 1h stated; we also run BTC as a separate leg
- Donchian 20 (length not stated; fair default), shift-1 so the signal bar is not in the channel
- ADX(14) > 20, Choppiness(14) < 40, close vs EMA 50
- Stop: 3 * ATR(14) from signal close (trail omitted in tradesim)
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from strategies.common.signal_sides import SideMode
from tradesim import Signal

STRATEGY_ID = "quant_tactics_donchian_adx"
STRATEGY_VERSION = "0.1.0"

DONCHIAN_N = 20
EMA_N = 50
ADX_N = 14
ADX_MIN = 20.0
CHOP_N = 14
CHOP_MAX = 40.0
ATR_N = 14
ATR_STOP_MULT = 3.0
WARMUP = max(DONCHIAN_N, EMA_N, ADX_N * 2, CHOP_N) + 4


def _rma(x: np.ndarray, n: int) -> np.ndarray:
    return pd.Series(x).ewm(alpha=1.0 / n, adjust=False, min_periods=n).mean().to_numpy(float)


def _atr(high: np.ndarray, low: np.ndarray, close: np.ndarray, n: int) -> np.ndarray:
    prev_c = np.roll(close, 1)
    prev_c[0] = close[0]
    tr = np.maximum(high - low, np.maximum(np.abs(high - prev_c), np.abs(low - prev_c)))
    return _rma(tr, n)


def _adx(high: np.ndarray, low: np.ndarray, close: np.ndarray, n: int) -> np.ndarray:
    prev_c = np.roll(close, 1)
    prev_h = np.roll(high, 1)
    prev_l = np.roll(low, 1)
    prev_c[0], prev_h[0], prev_l[0] = close[0], high[0], low[0]
    tr = np.maximum(high - low, np.maximum(np.abs(high - prev_c), np.abs(low - prev_c)))
    up_move = high - prev_h
    down_move = prev_l - low
    plus_dm = np.where((up_move > down_move) & (up_move > 0.0), up_move, 0.0)
    minus_dm = np.where((down_move > up_move) & (down_move > 0.0), down_move, 0.0)
    atr = _rma(tr, n)
    plus_di = 100.0 * _rma(plus_dm, n) / np.maximum(atr, 1e-12)
    minus_di = 100.0 * _rma(minus_dm, n) / np.maximum(atr, 1e-12)
    dx = 100.0 * np.abs(plus_di - minus_di) / np.maximum(plus_di + minus_di, 1e-12)
    return _rma(dx, n)


def _choppiness(high: np.ndarray, low: np.ndarray, close: np.ndarray, n: int) -> np.ndarray:
    atr = _atr(high, low, close, 1)
    atr_sum = pd.Series(atr).rolling(n, min_periods=n).sum().to_numpy(float)
    hh = pd.Series(high).rolling(n, min_periods=n).max().to_numpy(float)
    ll = pd.Series(low).rolling(n, min_periods=n).min().to_numpy(float)
    span = np.maximum(hh - ll, 1e-12)
    return 100.0 * np.log10(np.maximum(atr_sum / span, 1e-12)) / np.log10(float(n))


def build_signal_frame(df: pd.DataFrame) -> pd.DataFrame:
    out = df.sort_values("ts_ms").reset_index(drop=True).copy()
    h = out["high"].to_numpy(float)
    low = out["low"].to_numpy(float)
    c = out["close"].to_numpy(float)
    prior_high = pd.Series(h).rolling(DONCHIAN_N, min_periods=DONCHIAN_N).max().shift(1).to_numpy(float)
    prior_low = pd.Series(low).rolling(DONCHIAN_N, min_periods=DONCHIAN_N).min().shift(1).to_numpy(float)
    ema50 = pd.Series(c).ewm(span=EMA_N, adjust=False, min_periods=EMA_N).mean().to_numpy(float)
    adx = _adx(h, low, c, ADX_N)
    chop = _choppiness(h, low, c, CHOP_N)
    atr = _atr(h, low, c, ATR_N)
    filt = (adx > ADX_MIN) & (chop < CHOP_MAX)
    long_raw = (c > prior_high) & (c > ema50) & filt
    short_raw = (c < prior_low) & (c < ema50) & filt
    long_raw[:WARMUP] = short_raw[:WARMUP] = False
    both = long_raw & short_raw
    long_raw[both] = short_raw[both] = False
    stop = np.full(len(out), np.nan)
    stop[long_raw] = c[long_raw] - ATR_STOP_MULT * atr[long_raw]
    stop[short_raw] = c[short_raw] + ATR_STOP_MULT * atr[short_raw]
    out["donchian_prior_high"] = prior_high
    out["donchian_prior_low"] = prior_low
    out["ema50"] = ema50
    out["adx"] = adx
    out["chop"] = chop
    out["atr14"] = atr
    out["long_signal"] = long_raw
    out["short_signal"] = short_raw
    out["stop_price"] = stop
    out["target_price"] = np.nan
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
                    tag="qt_dc_l",
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
                    tag="qt_dc_s",
                )
            )
    return sigs
