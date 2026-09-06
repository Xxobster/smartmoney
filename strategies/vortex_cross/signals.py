"""Vortex Indicator 14, VI+ / VI− cross. Vectorized."""

from __future__ import annotations

import numpy as np
import pandas as pd

from strategies.common.signal_sides import SideMode
from tradesim import Signal

STRATEGY_ID = "vortex_cross"
STRATEGY_VERSION = "0.1.0"

VI_N = 14
ATR_N = 14
ATR_STOP = 2.0
RR = 1.5
WARMUP = VI_N + ATR_N + 2


def _atr(high: np.ndarray, low: np.ndarray, close: np.ndarray, n: int) -> np.ndarray:
    prev_c = np.roll(close, 1)
    prev_c[0] = close[0]
    tr = np.maximum(high - low, np.maximum(np.abs(high - prev_c), np.abs(low - prev_c)))
    return pd.Series(tr).ewm(alpha=1.0 / n, adjust=False, min_periods=n).mean().to_numpy(float)


def vortex_plus_minus(
    high: np.ndarray, low: np.ndarray, close: np.ndarray, n: int = 14
) -> tuple[np.ndarray, np.ndarray]:
    prev_c = np.roll(close, 1)
    prev_h = np.roll(high, 1)
    prev_l = np.roll(low, 1)
    prev_c[0] = close[0]
    prev_h[0] = high[0]
    prev_l[0] = low[0]
    tr = np.maximum(high - low, np.maximum(np.abs(high - prev_c), np.abs(low - prev_c)))
    vm_p = np.abs(high - prev_l)
    vm_m = np.abs(low - prev_h)
    tr_sum = pd.Series(tr).rolling(n, min_periods=n).sum()
    vip = (pd.Series(vm_p).rolling(n, min_periods=n).sum() / tr_sum.replace(0.0, np.nan)).to_numpy(
        float
    )
    vim = (pd.Series(vm_m).rolling(n, min_periods=n).sum() / tr_sum.replace(0.0, np.nan)).to_numpy(
        float
    )
    return vip, vim


def build_signal_frame(df: pd.DataFrame) -> pd.DataFrame:
    out = df.sort_values("ts_ms").reset_index(drop=True).copy()
    h = out["high"].to_numpy(float)
    low = out["low"].to_numpy(float)
    c = out["close"].to_numpy(float)
    vip, vim = vortex_plus_minus(h, low, c, VI_N)
    p_vip = np.roll(vip, 1)
    p_vim = np.roll(vim, 1)
    p_vip[0] = p_vim[0] = np.nan
    long_raw = (p_vip <= p_vim) & (vip > vim)
    short_raw = (p_vim <= p_vip) & (vim > vip)
    long_raw[:WARMUP] = False
    short_raw[:WARMUP] = False
    both = long_raw & short_raw
    long_raw[both] = short_raw[both] = False
    atr = _atr(h, low, c, ATR_N)
    stop = np.full(len(out), np.nan)
    target = np.full(len(out), np.nan)
    stop[long_raw] = c[long_raw] - ATR_STOP * atr[long_raw]
    target[long_raw] = c[long_raw] + RR * ATR_STOP * atr[long_raw]
    stop[short_raw] = c[short_raw] + ATR_STOP * atr[short_raw]
    target[short_raw] = c[short_raw] - RR * ATR_STOP * atr[short_raw]
    out["vi_plus"] = vip
    out["vi_minus"] = vim
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
                    tag="vtx_l",
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
                    tag="vtx_s",
                )
            )
    return sigs
