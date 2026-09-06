"""Krown hourly Relative Strength Index (RSI) momentum burst — vectorized, causal.

Fair H0 from Krown `hTcz81O2w-o` (stated four-rule recipe, not the 576-variant search):
- 1-hour RSI 14 fresh cross up through 70
- Close above 1-hour 200 Simple Moving Average (SMA)
- Completed 4-hour RSI 14 > 50 (lagged)
- Completed daily RSI 14 > 50 (lagged)
- Exit: time only, 24 hours later; no stop, no target
- Long-only source; short_mirror is the inverse (cross down 30, below SMA, HTF RSI < 50)

Do not copy his on-video 576-search winners (RSI-average exit, drop daily filter, etc.).
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from engine.features import lag_htf_to_ltf
from strategies.common.signal_sides import SideMode
from tradesim import Signal

STRATEGY_ID = "krown_rsi_momentum_burst"
STRATEGY_VERSION = "0.1.0"

RSI_N = 14
SMA_N = 200
RSI_CROSS = 70.0
RSI_CROSS_SHORT = 30.0
HTF_LEVEL = 50.0
WARMUP = SMA_N + RSI_N * 24 + 48


def _rsi(close: np.ndarray, n: int) -> np.ndarray:
    d = np.diff(close, prepend=close[0])
    up = np.where(d > 0.0, d, 0.0)
    dn = np.where(d < 0.0, -d, 0.0)
    ru = pd.Series(up).ewm(alpha=1.0 / n, adjust=False, min_periods=n).mean()
    rd = pd.Series(dn).ewm(alpha=1.0 / n, adjust=False, min_periods=n).mean()
    return (100.0 - 100.0 / (1.0 + ru / (rd + 1e-12))).to_numpy(float)


def _resample(df: pd.DataFrame, rule: str) -> pd.DataFrame:
    x = df.sort_values("ts_ms").copy()
    idx = pd.to_datetime(x["ts_ms"], unit="ms", utc=True)
    g = x.set_index(idx)
    r = g.resample(rule, label="left", closed="left").agg(
        {"open": "first", "high": "max", "low": "min", "close": "last", "volume": "sum"}
    )
    r = r.dropna(subset=["close"]).copy()
    r["ts_ms"] = np.array([int(t.timestamp() * 1000) for t in r.index], dtype=np.int64)
    return r.reset_index(drop=True)


def _htf_rsi(df: pd.DataFrame, rule: str, htf: str) -> np.ndarray:
    htf_df = _resample(df, rule)
    rsi = _rsi(htf_df["close"].to_numpy(float), RSI_N)
    feat = pd.DataFrame({"ts_ms": htf_df["ts_ms"].to_numpy(np.int64), "rsi14": rsi})
    aligned = lag_htf_to_ltf(df, feat, htf)
    return aligned["htf_rsi14"].to_numpy(float)


def build_signal_frame(df: pd.DataFrame) -> pd.DataFrame:
    out = df.sort_values("ts_ms").reset_index(drop=True).copy()
    c = out["close"].to_numpy(float)
    rsi = _rsi(c, RSI_N)
    sma = pd.Series(c).rolling(SMA_N, min_periods=SMA_N).mean().to_numpy(float)
    prev = np.roll(rsi, 1)
    prev[0] = np.nan
    rsi4 = _htf_rsi(out, "4h", "4h")
    rsi_d = _htf_rsi(out, "1D", "1d")
    long_raw = (
        (rsi > RSI_CROSS)
        & (prev <= RSI_CROSS)
        & (c > sma)
        & (rsi4 > HTF_LEVEL)
        & (rsi_d > HTF_LEVEL)
    )
    short_raw = (
        (rsi < RSI_CROSS_SHORT)
        & (prev >= RSI_CROSS_SHORT)
        & (c < sma)
        & (rsi4 < HTF_LEVEL)
        & (rsi_d < HTF_LEVEL)
    )
    both = long_raw & short_raw
    long_raw[both] = short_raw[both] = False
    long_raw[:WARMUP] = short_raw[:WARMUP] = False
    finite = np.isfinite(rsi) & np.isfinite(sma) & np.isfinite(rsi4) & np.isfinite(rsi_d)
    long_raw &= finite
    short_raw &= finite
    out["rsi14"] = rsi
    out["sma200"] = sma
    out["rsi4h"] = rsi4
    out["rsi1d"] = rsi_d
    out["long_signal"] = long_raw
    out["short_signal"] = short_raw
    return out


def to_tradesim_signals(
    feat: pd.DataFrame,
    symbol: str,
    max_hold_bars: int = 24,
    *,
    side_mode: SideMode = "long",
) -> list[Signal]:
    sigs: list[Signal] = []
    ts = feat["ts_ms"].to_numpy(np.int64)
    long_sig = feat["long_signal"].to_numpy(bool)
    short_sig = feat["short_signal"].to_numpy(bool)
    use_long = side_mode in ("long", "long_mirror")
    use_short = side_mode in ("short", "short_mirror")
    for i in range(len(feat)):
        if use_long and long_sig[i]:
            sigs.append(
                Signal(
                    ts_ms=int(ts[i]),
                    side=1,
                    symbol=symbol,
                    stop_price=None,
                    target_price=None,
                    max_hold_bars=max_hold_bars,
                    tag="kmb_l",
                )
            )
        elif use_short and short_sig[i]:
            sigs.append(
                Signal(
                    ts_ms=int(ts[i]),
                    side=-1,
                    symbol=symbol,
                    stop_price=None,
                    target_price=None,
                    max_hold_bars=max_hold_bars,
                    tag="kmb_s",
                )
            )
    return sigs
