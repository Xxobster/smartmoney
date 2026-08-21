"""Shim — implementation lives in live_candles (TSM-VPA ts_ms/ts shape)."""

from __future__ import annotations

import logging
import sqlite3
from pathlib import Path

import pandas as pd

from live_candles.reader import load_ohlcv, shared_db_path as _shared_db_path
from live_candles.shared import candles_fresh, interval_ms, latest_ts_ms

log = logging.getLogger(__name__)

DEFAULT_SHARED_DB = "/var/lib/botsgeneral/shared_candles.db"


def shared_db_path():
    return _shared_db_path()


def load_candles(
    symbol: str,
    interval: str,
    *,
    exchange: str = "bybit",
    db_path: Path | str | None = None,
) -> pd.DataFrame:
    """Load OHLCV shaped for strategy/engine: ts_ms, ts, open, high, low, close, volume."""
    empty = pd.DataFrame(columns=["ts_ms", "ts", "open", "high", "low", "close", "volume"])
    try:
        raw = load_ohlcv(exchange, symbol, interval, db_path=db_path)
    except Exception:
        log.exception("Failed reading shared candles %s %s %s", exchange, symbol, interval)
        return empty
    if raw is None or raw.empty:
        return empty
    df = raw[["ts_ms", "open", "high", "low", "close", "volume"]].copy()
    df = df.drop_duplicates(subset=["ts_ms"], keep="last").sort_values("ts_ms").reset_index(drop=True)
    df["ts"] = pd.to_datetime(df["ts_ms"], unit="ms", utc=True)
    return df[["ts_ms", "ts", "open", "high", "low", "close", "volume"]]


def candle_count(
    symbol: str,
    interval: str,
    *,
    exchange: str = "bybit",
    db_path: Path | str | None = None,
) -> int:
    path = Path(db_path) if db_path else shared_db_path()
    if not path.exists():
        return 0
    try:
        with sqlite3.connect(f"file:{path}?mode=ro", uri=True, timeout=30) as conn:
            row = conn.execute(
                """
                SELECT COUNT(*) FROM candles
                WHERE exchange=? AND symbol=? AND timeframe=?
                """,
                (exchange.lower(), symbol.upper(), interval.strip().lower()),
            ).fetchone()
        return int(row[0] or 0)
    except Exception:
        return 0


__all__ = [
    "DEFAULT_SHARED_DB",
    "shared_db_path",
    "interval_ms",
    "load_candles",
    "latest_ts_ms",
    "candles_fresh",
    "candle_count",
]
