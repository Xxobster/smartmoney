"""Public Binance USD-M kline fallback when the shared collector is late."""

from __future__ import annotations

import json
import logging
import time
import urllib.error
import urllib.request

import pandas as pd

log = logging.getLogger(__name__)

BINANCE_FUTURES_KLINES = "https://fapi.binance.com/fapi/v1/klines"
TF_MS = {
    "1m": 60_000,
    "5m": 300_000,
    "15m": 900_000,
    "1h": 3_600_000,
    "4h": 14_400_000,
    "1d": 86_400_000,
}


def fetch_closed_klines(
    symbol: str,
    timeframe: str,
    *,
    start_ms: int,
    limit: int = 8,
    now_ms: int | None = None,
    timeout_sec: float = 8.0,
) -> pd.DataFrame:
    """Return closed Last-price bars from Binance USD-M (bar open = ts_ms)."""
    empty = pd.DataFrame(columns=["ts_ms", "open", "high", "low", "close", "volume"])
    tf = timeframe.strip().lower()
    step = TF_MS.get(tf)
    if step is None:
        return empty
    now = int(now_ms if now_ms is not None else time.time() * 1000)
    url = (
        f"{BINANCE_FUTURES_KLINES}?symbol={symbol.upper()}"
        f"&interval={tf}&startTime={int(start_ms)}&limit={int(limit)}"
    )
    try:
        with urllib.request.urlopen(url, timeout=timeout_sec) as resp:
            raw = json.loads(resp.read().decode("utf-8"))
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, ValueError):
        log.exception("Binance kline fallback failed for %s %s", symbol, tf)
        return empty
    if not isinstance(raw, list) or not raw:
        return empty
    rows = []
    for k in raw:
        try:
            ts_ms = int(k[0])
            close_ms = int(k[6])
            if close_ms >= now:
                continue
            rows.append(
                {
                    "ts_ms": ts_ms,
                    "open": float(k[1]),
                    "high": float(k[2]),
                    "low": float(k[3]),
                    "close": float(k[4]),
                    "volume": float(k[5]),
                }
            )
        except (TypeError, ValueError, IndexError):
            continue
    if not rows:
        return empty
    return pd.DataFrame(rows).drop_duplicates("ts_ms").sort_values("ts_ms").reset_index(drop=True)


def merge_closed_bars(base: pd.DataFrame, extra: pd.DataFrame) -> pd.DataFrame:
    cols = ["ts_ms", "open", "high", "low", "close", "volume"]
    if extra is None or extra.empty:
        return base
    if base is None or base.empty:
        out = extra[cols].copy()
    else:
        out = pd.concat([base[cols], extra[cols]], ignore_index=True)
    out = out.drop_duplicates("ts_ms", keep="last").sort_values("ts_ms").reset_index(drop=True)
    if "ts" not in out.columns:
        out["ts"] = pd.to_datetime(out["ts_ms"], unit="ms", utc=True)
    return out


def series_gaps(ts_ms, step_ms: int = 3_600_000) -> list[tuple[int, int, int]]:
    """Return (prev_ts, next_ts, missing_bars) for each hole."""
    if ts_ms is None or len(ts_ms) < 2:
        return []
    out = []
    for a, b in zip(ts_ms[:-1], ts_ms[1:]):
        delta = int(b) - int(a)
        if delta > step_ms:
            out.append((int(a), int(b), int(delta // step_ms) - 1))
    return out
