"""UTC daily VWAP + RSI(14) consensus signals (causal)."""

from __future__ import annotations

import numpy as np
import pandas as pd

from tradesim import Signal

STRATEGY_ID = "tsm_vwap_rsi"
STRATEGY_VERSION = "0.1.0"


def wilder_rsi(close: np.ndarray, length: int = 14) -> np.ndarray:
    c = pd.Series(close, dtype=float)
    d = c.diff()
    gain = d.clip(lower=0.0)
    loss = (-d).clip(lower=0.0)
    avg_g = gain.ewm(alpha=1 / length, adjust=False, min_periods=length).mean()
    avg_l = loss.ewm(alpha=1 / length, adjust=False, min_periods=length).mean()
    rs = avg_g / avg_l.replace(0.0, np.nan)
    return (100 - 100 / (1 + rs)).to_numpy(float)


def session_vwap(ts_ms: np.ndarray, high: np.ndarray, low: np.ndarray, close: np.ndarray, volume: np.ndarray) -> np.ndarray:
    typical = (high + low + close) / 3.0
    day = ts_ms // 86_400_000
    pv = typical * volume
    df = pd.DataFrame({"day": day, "pv": pv, "vol": volume})
    g = df.groupby("day", sort=False)
    cum_pv = g["pv"].cumsum().to_numpy(float)
    cum_vol = g["vol"].cumsum().to_numpy(float)
    with np.errstate(divide="ignore", invalid="ignore"):
        vwap = np.where(cum_vol > 0, cum_pv / cum_vol, np.nan)
    return vwap


def build_signal_frame(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy().reset_index(drop=True)
    ts = out["ts_ms"].to_numpy(np.int64)
    h = out["high"].to_numpy(float)
    l = out["low"].to_numpy(float)
    c = out["close"].to_numpy(float)
    vol = out["volume"].to_numpy(float) if "volume" in out.columns else np.ones(len(out))
    vol = np.where(vol > 0, vol, 1.0)
    vwap = session_vwap(ts, h, l, c, vol)
    rsi = wilder_rsi(c, 14)
    out["vwap"] = vwap
    out["rsi14"] = rsi

    long_raw = (c > vwap) & (rsi > 50.0) & np.isfinite(vwap)
    short_raw = (c < vwap) & (rsi < 50.0) & np.isfinite(vwap)
    # cross into consensus
    long_sig = long_raw & ~np.roll(long_raw, 1)
    short_sig = short_raw & ~np.roll(short_raw, 1)
    long_sig[0] = short_sig[0] = False
    long_sig[:20] = False
    short_sig[:20] = False
    both = long_sig & short_sig
    long_sig[both] = short_sig[both] = False

    stop = np.full(len(out), np.nan)
    target = np.full(len(out), np.nan)
    prev_l = np.roll(l, 1)
    prev_h = np.roll(h, 1)
    prev_l[0] = l[0]
    prev_h[0] = h[0]
    stop[long_sig] = prev_l[long_sig] * (1 - 1e-4)
    risk = np.maximum(c[long_sig] - stop[long_sig], c[long_sig] * 1e-4)
    target[long_sig] = c[long_sig] + 2.5 * risk
    stop[short_sig] = prev_h[short_sig] * (1 + 1e-4)
    risk_s = np.maximum(stop[short_sig] - c[short_sig], c[short_sig] * 1e-4)
    target[short_sig] = c[short_sig] - 2.5 * risk_s

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
                    tag="tsm_vwap_rsi",
                )
            )
    return sigs
