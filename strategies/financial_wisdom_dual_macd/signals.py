"""Weekly + daily Moving Average Convergence Divergence (MACD) H0.

Fair freeze from Financial Wisdom `Gzl43lj2tS4` (long-only source):
- Standard MACD 12 / 26 / 9
- Weekly MACD above signal is a lagged completed-week filter
- Daily MACD cross above signal is the entry (short_mirror uses the inverse)
- Stop: signal-bar wick; MACD cross-down exit omitted (tradesim has no indicator exit)
- Long and short_mirror reported separately — never pooled
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from strategies.common.signal_sides import SideMode
from tradesim import Signal

STRATEGY_ID = "financial_wisdom_dual_macd"
STRATEGY_VERSION = "0.1.0"

FAST = 12
SLOW = 26
SIGNAL = 9
WARMUP = SLOW * 7 + SIGNAL + 8
WEEK_MS = 7 * 86_400_000


def _macd(close: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    c = pd.Series(close)
    fast = c.ewm(span=FAST, adjust=False, min_periods=FAST).mean()
    slow = c.ewm(span=SLOW, adjust=False, min_periods=SLOW).mean()
    line = fast - slow
    sig = line.ewm(span=SIGNAL, adjust=False, min_periods=SIGNAL).mean()
    return line.to_numpy(float), sig.to_numpy(float)


def _weekly_from_daily(df: pd.DataFrame) -> pd.DataFrame:
    x = df.sort_values("ts_ms").copy()
    idx = pd.to_datetime(x["ts_ms"], unit="ms", utc=True)
    g = x.set_index(idx)
    r = g.resample("7D", label="left", closed="left").agg(
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
    macd, sig = _macd(c)
    prev_m = np.roll(macd, 1)
    prev_s = np.roll(sig, 1)
    prev_m[0] = prev_s[0] = np.nan
    daily_up = (prev_m <= prev_s) & (macd > sig)
    daily_dn = (prev_m >= prev_s) & (macd < sig)

    week = _weekly_from_daily(out)
    w_line, w_sig = _macd(week["close"].to_numpy(float))
    w_feat = week[["ts_ms"]].copy()
    w_feat["macd"] = w_line
    w_feat["signal"] = w_sig
    w_feat["bull"] = w_line > w_sig
    right = w_feat.copy()
    right["available_ms"] = right["ts_ms"] + WEEK_MS
    merged = pd.merge_asof(
        out[["ts_ms"]].sort_values("ts_ms"),
        right[["available_ms", "bull"]].sort_values("available_ms"),
        left_on="ts_ms",
        right_on="available_ms",
        direction="backward",
    )
    weekly_bull = merged["bull"]
    weekly_ok = weekly_bull.fillna(False).to_numpy(bool)
    weekly_bear = (~weekly_bull.fillna(True)).to_numpy(bool)

    long_raw = daily_up & weekly_ok
    short_raw = daily_dn & weekly_bear
    long_raw[:WARMUP] = short_raw[:WARMUP] = False
    both = long_raw & short_raw
    long_raw[both] = short_raw[both] = False
    stop = np.full(len(out), np.nan)
    stop[long_raw] = low[long_raw]
    stop[short_raw] = h[short_raw]
    out["macd"] = macd
    out["macd_signal"] = sig
    out["weekly_bull"] = weekly_ok
    out["long_signal"] = long_raw
    out["short_signal"] = short_raw
    out["stop_price"] = stop
    return out


def to_tradesim_signals(
    feat: pd.DataFrame,
    symbol: str,
    max_hold_bars: int = 60,
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
                    tag="dmacd_l",
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
                    tag="dmacd_s",
                )
            )
    return sigs
