"""London opening-channel breakout (UTC hour 7 range, trade after 08:00)."""

from __future__ import annotations

import numpy as np
import pandas as pd

from tradesim import Signal

STRATEGY_ID = "tsm_london_opening_channel"
STRATEGY_VERSION = "0.1.0"


def ema(x: np.ndarray, n: int) -> np.ndarray:
    return pd.Series(x).ewm(span=n, adjust=False).mean().to_numpy(float)


def build_signal_frame(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy().reset_index(drop=True)
    ts = out["ts_ms"].to_numpy(np.int64)
    high = out["high"].to_numpy(float)
    low = out["low"].to_numpy(float)
    close = out["close"].to_numpy(float)
    e200 = ema(close, 200)
    out["ema200"] = e200

    day = ts // 86_400_000
    hour = ((ts // 3_600_000) % 24).astype(int)

    # Channel from hour==7 bars only (vectorized groupby)
    ch = pd.DataFrame({"day": day, "hour": hour, "high": high, "low": low})
    win = ch[ch["hour"] == 7].groupby("day").agg(ch_hi=("high", "max"), ch_lo=("low", "min"))
    mapped = ch[["day"]].merge(win, left_on="day", right_index=True, how="left")
    ch_hi = mapped["ch_hi"].to_numpy(float)
    ch_lo = mapped["ch_lo"].to_numpy(float)
    # Channel from hour-7 bar is known only after that bar closes → usable from hour>=8.
    known = hour >= 8
    ch_hi = np.where(known, ch_hi, np.nan)
    ch_lo = np.where(known, ch_lo, np.nan)
    out["channel_high"] = ch_hi
    out["channel_low"] = ch_lo

    width = ch_hi - ch_lo
    valid = known & (~np.isnan(ch_hi)) & (~np.isnan(ch_lo)) & (width > 0)

    # First break after 08:00 UTC per day
    n = len(out)
    long_sig = np.zeros(n, dtype=bool)
    short_sig = np.zeros(n, dtype=bool)
    stop = np.full(n, np.nan)
    target = np.full(n, np.nan)

    traded_day_long: set[int] = set()
    traded_day_short: set[int] = set()
    for i in range(n):
        if not valid[i] or hour[i] < 8:
            continue
        d = int(day[i])
        if d not in traded_day_long and close[i] > ch_hi[i] and close[i] > e200[i]:
            long_sig[i] = True
            stop[i] = ch_lo[i] * (1 - 1e-4)
            target[i] = close[i] + width[i]
            traded_day_long.add(d)
            traded_day_short.add(d)  # one directional attempt per day
        elif d not in traded_day_short and close[i] < ch_lo[i] and close[i] < e200[i]:
            short_sig[i] = True
            stop[i] = ch_hi[i] * (1 + 1e-4)
            target[i] = close[i] - width[i]
            traded_day_short.add(d)
            traded_day_long.add(d)

    out["long_signal"] = long_sig
    out["short_signal"] = short_sig
    out["stop_price"] = stop
    out["target_price"] = target
    return out


def to_tradesim_signals(feat: pd.DataFrame, symbol: str, max_hold_bars: int = 24) -> list[Signal]:
    sigs: list[Signal] = []
    ts = feat["ts_ms"].to_numpy(np.int64)
    for i in range(len(feat)):
        if bool(feat["long_signal"].iloc[i]) ^ bool(feat["short_signal"].iloc[i]):
            side = 1 if bool(feat["long_signal"].iloc[i]) else -1
            sp, tp = float(feat["stop_price"].iloc[i]), float(feat["target_price"].iloc[i])
            if np.isnan(sp) or np.isnan(tp):
                continue
            # skip inverted
            c = float(feat["close"].iloc[i])
            if side == 1 and not (sp < c < tp):
                continue
            if side == -1 and not (tp < c < sp):
                continue
            sigs.append(
                Signal(
                    ts_ms=int(ts[i]),
                    side=side,
                    symbol=symbol,
                    stop_price=sp,
                    target_price=tp,
                    max_hold_bars=max_hold_bars,
                    tag="tsm_london_ch",
                )
            )
    return sigs
