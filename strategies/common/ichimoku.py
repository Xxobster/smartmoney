"""Standard Hosoda Ichimoku (Tenkan 9, Kijun 26, Senkou B 52, displacement 26).

Cloud at bar *i* is the Senkou pair computed 26 bars ago (the forward plot is
display-only; using current Senkou as "today's cloud" would leak). Chikou
breakout compares this bar's close to the high/low of the candle 26 bars ago.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from engine.features import lag_htf_to_ltf
from strategies.common.signal_sides import SideMode
from tradesim import Signal

TENKAN_N = 9
KIJUN_N = 26
SENKOU_B_N = 52
DISPLACE = 26
RR = 2.0
WARMUP_LTF = SENKOU_B_N + DISPLACE + 2
# Daily Ichimoku needs 52+26 completed days; 4-hour bars × 6 per day, plus slack.
WARMUP_DOUBLE = (SENKOU_B_N + DISPLACE + 8) * 6


def shift_nan(a: np.ndarray, n: int) -> np.ndarray:
    x = np.asarray(a, dtype=float)
    out = np.full(x.shape, np.nan, dtype=float)
    if n <= 0:
        return x.copy()
    if x.size <= n:
        return out
    out[n:] = x[:-n]
    return out


def hl_midpoint(high: np.ndarray, low: np.ndarray, n: int) -> np.ndarray:
    hh = pd.Series(high).rolling(n, min_periods=n).max().to_numpy(float)
    ll = pd.Series(low).rolling(n, min_periods=n).min().to_numpy(float)
    return (hh + ll) * 0.5


def add_ichimoku_columns(out: pd.DataFrame) -> pd.DataFrame:
    """Add causal Ichimoku columns in place; returns the same frame."""
    h = out["high"].to_numpy(float)
    low = out["low"].to_numpy(float)
    c = out["close"].to_numpy(float)
    tenkan = hl_midpoint(h, low, TENKAN_N)
    kijun = hl_midpoint(h, low, KIJUN_N)
    span_a_src = (tenkan + kijun) * 0.5
    span_b_src = hl_midpoint(h, low, SENKOU_B_N)
    cloud_a = shift_nan(span_a_src, DISPLACE)
    cloud_b = shift_nan(span_b_src, DISPLACE)
    h26 = shift_nan(h, DISPLACE)
    low26 = shift_nan(low, DISPLACE)
    h27 = shift_nan(h, DISPLACE + 1)
    low27 = shift_nan(low, DISPLACE + 1)
    c1 = shift_nan(c, 1)
    out["tenkan"] = tenkan
    out["kijun"] = kijun
    out["cloud_a"] = cloud_a
    out["cloud_b"] = cloud_b
    out["cloud_top"] = np.fmax(cloud_a, cloud_b)
    out["cloud_bot"] = np.fmin(cloud_a, cloud_b)
    out["chikou_break_up"] = (c > h26) & (c1 <= h27)
    out["chikou_break_dn"] = (c < low26) & (c1 >= low27)
    return out


def _resample_daily(df: pd.DataFrame) -> pd.DataFrame:
    x = df.sort_values("ts_ms").copy()
    idx = pd.to_datetime(x["ts_ms"], unit="ms", utc=True)
    g = x.set_index(idx)
    r = g.resample("1D", label="left", closed="left").agg(
        {"open": "first", "high": "max", "low": "min", "close": "last", "volume": "sum"}
    )
    r = r.dropna(subset=["close"]).copy()
    r["ts_ms"] = np.array([int(t.timestamp() * 1000) for t in r.index], dtype=np.int64)
    return r.reset_index(drop=True)


def daily_tk_cloud_bias(ltf: pd.DataFrame) -> tuple[np.ndarray, np.ndarray]:
    """Completed lagged daily: close vs cloud and Tenkan vs Kijun."""
    daily = add_ichimoku_columns(_resample_daily(ltf))
    c = daily["close"].to_numpy(float)
    feat = pd.DataFrame({"ts_ms": daily["ts_ms"].to_numpy(np.int64)})
    feat["bull"] = (c > daily["cloud_top"].to_numpy(float)) & (
        daily["tenkan"].to_numpy(float) > daily["kijun"].to_numpy(float)
    )
    feat["bear"] = (c < daily["cloud_bot"].to_numpy(float)) & (
        daily["tenkan"].to_numpy(float) < daily["kijun"].to_numpy(float)
    )
    aligned = lag_htf_to_ltf(ltf, feat, "1d")
    bull = aligned["htf_bull"].fillna(False).to_numpy(bool)
    bear = aligned["htf_bear"].fillna(False).to_numpy(bool)
    return bull, bear


def build_ichimoku_signal_frame(
    df: pd.DataFrame,
    *,
    require_daily_bias: bool,
) -> pd.DataFrame:
    out = df.sort_values("ts_ms").reset_index(drop=True).copy()
    add_ichimoku_columns(out)
    tenkan = out["tenkan"].to_numpy(float)
    kijun = out["kijun"].to_numpy(float)
    c = out["close"].to_numpy(float)
    ch_up = out["chikou_break_up"].to_numpy(bool)
    ch_dn = out["chikou_break_dn"].to_numpy(bool)
    long_raw = (tenkan > kijun) & ch_up
    short_raw = (tenkan < kijun) & ch_dn
    warmup = WARMUP_DOUBLE if require_daily_bias else WARMUP_LTF
    if require_daily_bias:
        bull, bear = daily_tk_cloud_bias(out)
        out["htf_bull"] = bull
        out["htf_bear"] = bear
        long_raw &= bull
        short_raw &= bear
    both = long_raw & short_raw
    long_raw[both] = short_raw[both] = False
    long_raw[:warmup] = short_raw[:warmup] = False
    finite = np.isfinite(tenkan) & np.isfinite(kijun)
    long_raw &= finite
    short_raw &= finite
    stop = np.full(len(out), np.nan)
    target = np.full(len(out), np.nan)
    stop[long_raw] = kijun[long_raw]
    risk_l = c[long_raw] - stop[long_raw]
    target[long_raw] = c[long_raw] + RR * risk_l
    stop[short_raw] = kijun[short_raw]
    risk_s = stop[short_raw] - c[short_raw]
    target[short_raw] = c[short_raw] - RR * risk_s
    out["long_signal"] = long_raw
    out["short_signal"] = short_raw
    out["stop_price"] = stop
    out["target_price"] = target
    return out


def to_ichimoku_tradesim_signals(
    feat: pd.DataFrame,
    symbol: str,
    max_hold_bars: int = 48,
    *,
    side_mode: SideMode = "long",
    tag_prefix: str = "ichi",
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
                    tag=f"{tag_prefix}_l",
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
                    tag=f"{tag_prefix}_s",
                )
            )
    return sigs
