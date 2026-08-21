"""Live entry timing for 1h chandelier signals."""

from __future__ import annotations

import time
from dataclasses import dataclass

import pandas as pd

from chand.signals_core import build_signal_frame

TF_MS = {
    "1m": 60_000,
    "5m": 300_000,
    "15m": 900_000,
    "1h": 3_600_000,
    "4h": 14_400_000,
    "1d": 86_400_000,
}


@dataclass
class LiveSignal:
    side: str  # long | short
    signal_ts_ms: int  # open of decision (closed) bar
    entry_ts_ms: int  # open of next bar (executable)
    entry_ref_price: float
    stop_price: float
    target_price: float
    pattern: str = "chand_atr_band"
    stack_score: float = 1.0


def signals_from_frame(feat: pd.DataFrame, *, timeframe: str = "1h") -> list[LiveSignal]:
    step = TF_MS.get(timeframe.strip().lower(), 3_600_000)
    out: list[LiveSignal] = []
    ts = feat["ts_ms"].to_numpy()
    for i in range(len(feat)):
        long_i = bool(feat["long_signal"].iloc[i])
        short_i = bool(feat["short_signal"].iloc[i])
        if long_i == short_i:
            continue
        side = "long" if long_i else "short"
        sp = float(feat["stop_price"].iloc[i])
        tp = float(feat["target_price"].iloc[i])
        px = float(feat["close"].iloc[i])
        if not (sp == sp and tp == tp):
            continue
        if side == "long" and not (sp < px < tp):
            continue
        if side == "short" and not (tp < px < sp):
            continue
        decision = int(ts[i])
        out.append(
            LiveSignal(
                side=side,
                signal_ts_ms=decision,
                entry_ts_ms=decision + step,
                entry_ref_price=px,
                stop_price=sp,
                target_price=tp,
            )
        )
    return out


def generate_live_signals(df: pd.DataFrame, *, timeframe: str = "1h") -> list[LiveSignal]:
    feat = build_signal_frame(df)
    return signals_from_frame(feat, timeframe=timeframe)


def actionable_signal(
    signals: list[LiveSignal],
    *,
    last_closed_ts_ms: int,
    timeframe: str,
    now_ms: int | None = None,
) -> LiveSignal | None:
    """After bar T closes, entry is at open of T+1 (= last_closed + interval)."""
    step = TF_MS.get(timeframe.strip().lower(), 3_600_000)
    expected_entry = int(last_closed_ts_ms) + int(step)
    now = now_ms if now_ms is not None else int(time.time() * 1000)
    if now < expected_entry:
        return None
    matches = [s for s in signals if int(s.entry_ts_ms) == expected_entry]
    if not matches:
        return None
    return matches[-1]
