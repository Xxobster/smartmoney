"""ADX>25 + DI cross + OBV vs SMA100 (causal, vectorized Wilder)."""

from __future__ import annotations

import numpy as np
import pandas as pd

from tradesim import Signal

STRATEGY_ID = "tsm_adx_dmi_obv"
STRATEGY_VERSION = "0.1.0"


def wilder_adx(high, low, close, length=14):
    prev_c = np.roll(close, 1)
    prev_c[0] = close[0]
    prev_h = np.roll(high, 1)
    prev_l = np.roll(low, 1)
    prev_h[0], prev_l[0] = high[0], low[0]
    up = high - prev_h
    dn = prev_l - low
    plus_dm = np.where((up > dn) & (up > 0), up, 0.0)
    minus_dm = np.where((dn > up) & (dn > 0), dn, 0.0)
    tr = np.maximum(high - low, np.maximum(np.abs(high - prev_c), np.abs(low - prev_c)))
    atr = pd.Series(tr).ewm(alpha=1 / length, adjust=False, min_periods=length).mean()
    plus_di = 100 * pd.Series(plus_dm).ewm(alpha=1 / length, adjust=False, min_periods=length).mean() / atr
    minus_di = 100 * pd.Series(minus_dm).ewm(alpha=1 / length, adjust=False, min_periods=length).mean() / atr
    dx = (100 * (plus_di - minus_di).abs() / (plus_di + minus_di).replace(0, np.nan)).fillna(0)
    adx = dx.ewm(alpha=1 / length, adjust=False, min_periods=length).mean()
    return adx.to_numpy(float), plus_di.to_numpy(float), minus_di.to_numpy(float)


def atr(h, l, c, n=14):
    prev = np.roll(c, 1)
    prev[0] = c[0]
    tr = np.maximum(h - l, np.maximum(np.abs(h - prev), np.abs(l - prev)))
    return pd.Series(tr).ewm(alpha=1 / n, adjust=False, min_periods=n).mean().to_numpy(float)


def build_signal_frame(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy().reset_index(drop=True)
    h = out["high"].to_numpy(float)
    l = out["low"].to_numpy(float)
    c = out["close"].to_numpy(float)
    vol = out["volume"].to_numpy(float) if "volume" in out.columns else np.ones(len(out))
    adx, plus_di, minus_di = wilder_adx(h, l, c, 14)
    direction = np.sign(c - np.roll(c, 1))
    direction[0] = 0
    obv = np.cumsum(direction * vol)
    obv_sma = pd.Series(obv).rolling(100, min_periods=100).mean().to_numpy(float)
    di_up = (plus_di > minus_di) & (np.roll(plus_di, 1) <= np.roll(minus_di, 1))
    di_dn = (plus_di < minus_di) & (np.roll(plus_di, 1) >= np.roll(minus_di, 1))
    di_up[0] = di_dn[0] = False
    obv_up = (obv > obv_sma) & (np.roll(obv, 1) <= np.roll(obv_sma, 1))
    obv_dn = (obv < obv_sma) & (np.roll(obv, 1) >= np.roll(obv_sma, 1))
    obv_up[0] = obv_dn[0] = False
    # agree within 3 bars: DI cross now and OBV cross in last 3, or vice versa
    obv_up_w = obv_up.copy()
    obv_dn_w = obv_dn.copy()
    for k in (1, 2):
        obv_up_w |= np.roll(obv_up, k)
        obv_dn_w |= np.roll(obv_dn, k)
    obv_up_w[:3] = obv_dn_w[:3] = False
    di_up_w = di_up.copy()
    di_dn_w = di_dn.copy()
    for k in (1, 2):
        di_up_w |= np.roll(di_up, k)
        di_dn_w |= np.roll(di_dn, k)
    di_up_w[:3] = di_dn_w[:3] = False
    long_raw = (adx > 25) & ((di_up & obv_up_w) | (obv_up & di_up_w))
    short_raw = (adx > 25) & ((di_dn & obv_dn_w) | (obv_dn & di_dn_w))
    long_sig = long_raw & ~np.roll(long_raw, 1)
    short_sig = short_raw & ~np.roll(short_raw, 1)
    long_sig[0] = short_sig[0] = False
    long_sig[:120] = short_sig[:120] = False
    both = long_sig & short_sig
    long_sig[both] = short_sig[both] = False
    a = atr(h, l, c, 14)

    stop = np.full(len(out), np.nan)
    target = np.full(len(out), np.nan)
    stop[long_sig] = c[long_sig] - 1.5 * a[long_sig]
    risk = np.maximum(c[long_sig] - stop[long_sig], c[long_sig] * 1e-4)
    target[long_sig] = c[long_sig] + 2.0 * risk
    stop[short_sig] = c[short_sig] + 1.5 * a[short_sig]
    risk_s = np.maximum(stop[short_sig] - c[short_sig], c[short_sig] * 1e-4)
    target[short_sig] = c[short_sig] - 2.0 * risk_s

    out["adx"] = adx
    out["plus_di"] = plus_di
    out["minus_di"] = minus_di
    out["obv"] = obv
    out["long_signal"] = long_sig
    out["short_signal"] = short_sig
    out["stop_price"] = stop
    out["target_price"] = target
    return out


def to_tradesim_signals(feat: pd.DataFrame, symbol: str, max_hold_bars: int = 36) -> list[Signal]:
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
                    tag="tsm_adx_obv",
                )
            )
    return sigs
