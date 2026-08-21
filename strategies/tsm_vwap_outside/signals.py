"""1h EMA50 bias + 15m VWAP outside-candle entries."""

from __future__ import annotations

import numpy as np
import pandas as pd

from tradesim import Signal

STRATEGY_ID = "tsm_vwap_outside"
STRATEGY_VERSION = "0.1.0"


def ema(x: np.ndarray, n: int) -> np.ndarray:
    return pd.Series(x).ewm(span=n, adjust=False).mean().to_numpy(float)


def session_vwap(ts_ms, high, low, close, volume) -> np.ndarray:
    typical = (high + low + close) / 3.0
    day = ts_ms // 86_400_000
    df = pd.DataFrame({"day": day, "pv": typical * volume, "vol": volume})
    cum_pv = df.groupby("day", sort=False)["pv"].cumsum().to_numpy(float)
    cum_vol = df.groupby("day", sort=False)["vol"].cumsum().to_numpy(float)
    with np.errstate(divide="ignore", invalid="ignore"):
        return np.where(cum_vol > 0, cum_pv / cum_vol, np.nan)


def map_htf_bias(ltf_ts: np.ndarray, htf: pd.DataFrame) -> np.ndarray:
    """Causal: at ltf bar t, use last completed 1h bar's close vs EMA50."""
    htf = htf.sort_values("ts_ms").reset_index(drop=True)
    hc = htf["close"].to_numpy(float)
    ht = htf["ts_ms"].to_numpy(np.int64)
    e = ema(hc, 50)
    # bias known after htf bar closes → use values shifted by 1 completed bar
    bias = np.where(hc > e, 1, np.where(hc < e, -1, 0)).astype(np.int8)
    # asof merge: for each ltf ts, last htf with ht + 1h <= ltf_ts (completed)
    htf_end = ht + 3_600_000
    idx = np.searchsorted(htf_end, ltf_ts, side="right") - 1
    out = np.zeros(len(ltf_ts), dtype=np.int8)
    valid = idx >= 0
    out[valid] = bias[idx[valid]]
    # zero until ema warm
    warm = idx >= 50
    out[~warm] = 0
    return out


def build_signal_frame(df: pd.DataFrame, htf_1h: pd.DataFrame | None = None) -> pd.DataFrame:
    out = df.copy().reset_index(drop=True)
    ts = out["ts_ms"].to_numpy(np.int64)
    o = out["open"].to_numpy(float)
    h = out["high"].to_numpy(float)
    l = out["low"].to_numpy(float)
    c = out["close"].to_numpy(float)
    vol = out["volume"].to_numpy(float) if "volume" in out.columns else np.ones(len(out))
    vol = np.where(vol > 0, vol, 1.0)
    vwap = session_vwap(ts, h, l, c, vol)
    if htf_1h is None or htf_1h.empty:
        # fallback: same-TF EMA50 bias
        e50 = ema(c, 50)
        bias = np.where(c > e50, 1, -1).astype(np.int8)
        bias[:50] = 0
    else:
        bias = map_htf_bias(ts, htf_1h)

    prev_h = np.roll(h, 1)
    prev_l = np.roll(l, 1)
    prev_o = np.roll(o, 1)
    prev_c = np.roll(c, 1)
    prev_h[0] = h[0]
    prev_l[0] = l[0]
    outside = (h > prev_h) & (l < prev_l)
    bull_out = outside & (c > o) & (c > prev_o) & (c > prev_c)
    bear_out = outside & (c < o) & (c < prev_o) & (c < prev_c)
    thru_vwap = (l <= vwap) & (h >= vwap) & np.isfinite(vwap)

    long_raw = bull_out & thru_vwap & (bias > 0)
    short_raw = bear_out & thru_vwap & (bias < 0)
    long_sig = long_raw & ~np.roll(long_raw, 1)
    short_sig = short_raw & ~np.roll(short_raw, 1)
    long_sig[0] = short_sig[0] = False

    stop = np.full(len(out), np.nan)
    target = np.full(len(out), np.nan)
    stop[long_sig] = l[long_sig] * (1 - 1e-4)
    risk = np.maximum(c[long_sig] - stop[long_sig], c[long_sig] * 1e-4)
    target[long_sig] = c[long_sig] + 2.0 * risk
    stop[short_sig] = h[short_sig] * (1 + 1e-4)
    risk_s = np.maximum(stop[short_sig] - c[short_sig], c[short_sig] * 1e-4)
    target[short_sig] = c[short_sig] - 2.0 * risk_s

    out["vwap"] = vwap
    out["htf_bias"] = bias
    out["long_signal"] = long_sig
    out["short_signal"] = short_sig
    out["stop_price"] = stop
    out["target_price"] = target
    return out


def to_tradesim_signals(feat: pd.DataFrame, symbol: str, max_hold_bars: int = 32) -> list[Signal]:
    sigs: list[Signal] = []
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
                    tag="tsm_vwap_out",
                )
            )
    return sigs
