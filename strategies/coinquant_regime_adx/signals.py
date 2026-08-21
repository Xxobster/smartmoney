"""ADX regime + Bollinger reclaim. Vectorized; 4h regression uses completed bars."""

from __future__ import annotations

import numpy as np
import pandas as pd

from tradesim import Signal

STRATEGY_ID = "coinquant_regime_adx"
STRATEGY_VERSION = "0.1.0"

ADX_N = 14
ADX_TREND = 20.0
ADX_RANGE = 16.0
BB_N = 20
BB_K = 2.0
RSI_N = 14
LINREG_HTF = 50
LINREG_SLOPE_N = 100
HTF_MS = 14_400_000
SL_PCT = 0.015
TP_PCT = 0.055
WARMUP = 220


def _rma(x: np.ndarray, n: int) -> np.ndarray:
    return pd.Series(x).ewm(alpha=1.0 / n, adjust=False, min_periods=n).mean().to_numpy(float)


def _rsi(close: np.ndarray, n: int) -> np.ndarray:
    d = np.diff(close, prepend=close[0])
    up = np.where(d > 0.0, d, 0.0)
    dn = np.where(d < 0.0, -d, 0.0)
    ru, rd = _rma(up, n), _rma(dn, n)
    rs = ru / np.maximum(rd, 1e-12)
    return 100.0 - (100.0 / (1.0 + rs))


def _adx(high: np.ndarray, low: np.ndarray, close: np.ndarray, n: int) -> np.ndarray:
    prev_c = np.roll(close, 1)
    prev_c[0] = close[0]
    prev_h = np.roll(high, 1)
    prev_l = np.roll(low, 1)
    prev_h[0], prev_l[0] = high[0], low[0]
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


def _rolling_linreg_last(y: np.ndarray, n: int) -> tuple[np.ndarray, np.ndarray]:
    """OLS line value at the last point of each window, and slope."""
    out_v = np.full(len(y), np.nan)
    out_s = np.full(len(y), np.nan)
    if len(y) < n:
        return out_v, out_s
    x = np.arange(n, dtype=float)
    sx = x.sum()
    sxx = float(x @ x)
    den = n * sxx - sx * sx
    csum = np.cumsum(np.insert(y.astype(float), 0, 0.0))
    sy = csum[n:] - csum[:-n]
    # sum x*y for each window via convolution with x[::-1] on y
    kernel = x[::-1]
    sxy = np.convolve(y.astype(float), kernel, mode="valid")
    slope = (n * sxy - sx * sy) / den
    intercept = (sy - slope * sx) / n
    last = intercept + slope * (n - 1)
    out_v[n - 1 :] = last
    out_s[n - 1 :] = slope
    return out_v, out_s


def _completed_htf_close(ts_ms: np.ndarray, close: np.ndarray) -> np.ndarray:
    """Last close of the previous completed 4h bucket, aligned to each 1h bar."""
    bucket = ts_ms // HTF_MS
    df = pd.DataFrame({"bucket": bucket, "c": close})
    htf = df.groupby("bucket", sort=True)["c"].last()
    completed = htf.shift(1)
    mapped = pd.Series(bucket).map(completed)
    return mapped.to_numpy(float)


def build_signal_frame(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy().reset_index(drop=True)
    ts = out["ts_ms"].to_numpy(np.int64)
    h = out["high"].to_numpy(float)
    low = out["low"].to_numpy(float)
    c = out["close"].to_numpy(float)
    adx = _adx(h, low, c, ADX_N)
    rsi = _rsi(c, RSI_N)
    mid = pd.Series(c).rolling(BB_N, min_periods=BB_N).mean().to_numpy(float)
    std = pd.Series(c).rolling(BB_N, min_periods=BB_N).std(ddof=0).to_numpy(float)
    lower = mid - BB_K * std
    prev_c = np.roll(c, 1)
    prev_l = np.roll(lower, 1)
    prev_c[0] = prev_l[0] = np.nan
    cross_up_lower = (c > lower) & (prev_c <= prev_l)
    cross_dn_upper = (c < (mid + BB_K * std)) & (np.roll(c, 1) >= np.roll(mid + BB_K * std, 1))
    htf_c = _completed_htf_close(ts, c)
    # 4h series in time order of unique completed buckets
    bucket = ts // HTF_MS
    uniq = pd.DataFrame({"b": bucket, "htf": htf_c}).dropna().drop_duplicates("b")
    lin_v = np.full(len(out), np.nan)
    if len(uniq) >= LINREG_HTF:
        vv, _ = _rolling_linreg_last(uniq["htf"].to_numpy(float), LINREG_HTF)
        lin_map = dict(zip(uniq["b"].to_numpy(), vv, strict=False))
        lin_v = pd.Series(bucket).map(lin_map).to_numpy(float)
    _, slope = _rolling_linreg_last(c, LINREG_SLOPE_N)
    trend = adx > ADX_TREND
    ranging = adx < ADX_RANGE
    long_trend = trend & (c > lin_v) & (slope > 0.0) & cross_up_lower & (rsi > 20.0)
    short_trend = trend & (c < lin_v) & (slope < 0.0) & cross_dn_upper & (rsi < 80.0)
    long_range = ranging & cross_up_lower & (rsi < 35.0)
    short_range = ranging & cross_dn_upper & (rsi > 65.0)
    long_sig = long_trend | long_range
    short_sig = short_trend | short_range
    long_sig[:WARMUP] = False
    short_sig[:WARMUP] = False
    both = long_sig & short_sig
    long_sig[both] = short_sig[both] = False
    stop = np.full(len(out), np.nan)
    target = np.full(len(out), np.nan)
    stop[long_sig] = c[long_sig] * (1.0 - SL_PCT)
    target[long_sig] = c[long_sig] * (1.0 + TP_PCT)
    stop[short_sig] = c[short_sig] * (1.0 + SL_PCT)
    target[short_sig] = c[short_sig] * (1.0 - TP_PCT)
    out["adx"] = adx
    out["rsi"] = rsi
    out["bb_lower"] = lower
    out["linreg_htf"] = lin_v
    out["linreg_slope"] = slope
    out["long_signal"] = long_sig
    out["short_signal"] = short_sig
    out["stop_price"] = stop
    out["target_price"] = target
    return out


def to_tradesim_signals(feat: pd.DataFrame, symbol: str, max_hold_bars: int = 96) -> list[Signal]:
    sigs: list[Signal] = []
    ts = feat["ts_ms"].to_numpy(np.int64)
    long_sig = feat["long_signal"].to_numpy(bool)
    short_sig = feat["short_signal"].to_numpy(bool)
    stop = feat["stop_price"].to_numpy(float)
    target = feat["target_price"].to_numpy(float)
    px = feat["close"].to_numpy(float)
    for i in range(len(feat)):
        p = float(px[i])
        if long_sig[i]:
            sp, tp = float(stop[i]), float(target[i])
            if sp < p < tp:
                sigs.append(
                    Signal(
                        ts_ms=int(ts[i]),
                        side=1,
                        symbol=symbol,
                        stop_price=sp,
                        target_price=tp,
                        max_hold_bars=max_hold_bars,
                        tag="cq_adx_l",
                    )
                )
        elif short_sig[i]:
            sp, tp = float(stop[i]), float(target[i])
            if tp < p < sp:
                sigs.append(
                    Signal(
                        ts_ms=int(ts[i]),
                        side=-1,
                        symbol=symbol,
                        stop_price=sp,
                        target_price=tp,
                        max_hold_bars=max_hold_bars,
                        tag="cq_adx_s",
                    )
                )
    return sigs
