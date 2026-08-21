"""HI-LO SMA channel break with Heikin Ashi + ADX filter (causal)."""

from __future__ import annotations

import numpy as np
import pandas as pd

from tradesim import Signal

STRATEGY_ID = "tsm_hilo_ha_adx"
STRATEGY_VERSION = "0.1.0"


def heikin_ashi(o, h, l, c):
    n = len(c)
    ha_c = (o + h + l + c) / 4.0
    ha_o = np.empty(n, float)
    ha_o[0] = (o[0] + c[0]) / 2.0
    for i in range(1, n):
        ha_o[i] = (ha_o[i - 1] + ha_c[i - 1]) / 2.0
    return ha_o, ha_c


def wilder_adx(high, low, close, length=14):
    h = pd.Series(high, dtype=float)
    l = pd.Series(low, dtype=float)
    c = pd.Series(close, dtype=float)
    up = h.diff()
    dn = -l.diff()
    plus_dm = pd.Series(np.where((up > dn) & (up > 0), up, 0.0))
    minus_dm = pd.Series(np.where((dn > up) & (dn > 0), dn, 0.0))
    tr = pd.concat([(h - l), (h - c.shift()).abs(), (l - c.shift()).abs()], axis=1).max(axis=1)
    atr = tr.ewm(alpha=1 / length, adjust=False, min_periods=length).mean()
    plus_di = 100 * plus_dm.ewm(alpha=1 / length, adjust=False, min_periods=length).mean() / atr
    minus_di = 100 * minus_dm.ewm(alpha=1 / length, adjust=False, min_periods=length).mean() / atr
    dx = 100 * (plus_di - minus_di).abs() / (plus_di + minus_di).replace(0.0, np.nan)
    return dx.ewm(alpha=1 / length, adjust=False, min_periods=length).mean().to_numpy(float)


def build_signal_frame(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy().reset_index(drop=True)
    o = out["open"].to_numpy(float)
    h = out["high"].to_numpy(float)
    l = out["low"].to_numpy(float)
    c = out["close"].to_numpy(float)
    ch_hi = pd.Series(h).rolling(50, min_periods=50).mean().to_numpy(float)
    ch_lo = pd.Series(l).rolling(50, min_periods=50).mean().to_numpy(float)
    ha_o, ha_c = heikin_ashi(o, h, l, c)
    adx = wilder_adx(h, l, c, 14)
    out["channel_high"] = ch_hi
    out["channel_low"] = ch_lo
    out["ha_close"] = ha_c
    out["ha_open"] = ha_o
    out["adx14"] = adx

    ha_bull = ha_c > ha_o
    ha_bear = ha_c < ha_o
    long_raw = (c > ch_hi) & ha_bull & (adx > 20.0) & np.isfinite(ch_hi)
    short_raw = (c < ch_lo) & ha_bear & (adx > 20.0) & np.isfinite(ch_lo)
    long_sig = long_raw & ~np.roll(long_raw, 1)
    short_sig = short_raw & ~np.roll(short_raw, 1)
    long_sig[0] = short_sig[0] = False
    long_sig[:50] = False
    short_sig[:50] = False
    both = long_sig & short_sig
    long_sig[both] = short_sig[both] = False

    stop = np.full(len(out), np.nan)
    target = np.full(len(out), np.nan)
    stop[long_sig] = ch_lo[long_sig] * (1 - 1e-4)
    risk = np.maximum(c[long_sig] - stop[long_sig], c[long_sig] * 1e-4)
    target[long_sig] = c[long_sig] + 3.0 * risk
    stop[short_sig] = ch_hi[short_sig] * (1 + 1e-4)
    risk_s = np.maximum(stop[short_sig] - c[short_sig], c[short_sig] * 1e-4)
    target[short_sig] = c[short_sig] - 3.0 * risk_s

    out["long_signal"] = long_sig
    out["short_signal"] = short_sig
    out["stop_price"] = stop
    out["target_price"] = target
    return out


def to_tradesim_signals(feat: pd.DataFrame, symbol: str, max_hold_bars: int = 48) -> list[Signal]:
    sigs = []
    ts = feat["ts_ms"].to_numpy(np.int64)
    for i in range(len(feat)):
        if bool(feat["long_signal"].iloc[i]) ^ bool(feat["short_signal"].iloc[i]):
            side = 1 if bool(feat["long_signal"].iloc[i]) else -1
            sp, tp = float(feat["stop_price"].iloc[i]), float(feat["target_price"].iloc[i])
            if np.isnan(sp) or np.isnan(tp):
                continue
            px = float(feat["close"].iloc[i])
            if side == 1 and not (sp < px < tp):
                continue
            if side == -1 and not (tp < px < sp):
                continue
            sigs.append(
                Signal(
                    ts_ms=int(ts[i]),
                    side=side,
                    symbol=symbol,
                    stop_price=sp,
                    target_price=tp,
                    max_hold_bars=max_hold_bars,
                    tag="tsm_hilo_ha",
                )
            )
    return sigs
