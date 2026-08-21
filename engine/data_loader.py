"""Load OHLCV from research or lockbox SQLite; never mix them."""
from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Optional

import pandas as pd

from paths import DATASETS


def load_ohlcv(
    db_path: Path,
    symbol: str,
    timeframe: str,
    source: str = "binance",
    start_ms: Optional[int] = None,
    end_ms: Optional[int] = None,
) -> pd.DataFrame:
    conn = sqlite3.connect(str(db_path))
    try:
        q = """
        SELECT source, symbol, timeframe, ts_ms, open, high, low, close, volume,
               price_type, is_complete
        FROM market_ohlcv
        WHERE source = ? AND symbol = ? AND timeframe = ?
          AND is_complete = 1
        """
        params: list = [source, symbol, timeframe]
        if start_ms is not None:
            q += " AND ts_ms >= ?"
            params.append(start_ms)
        if end_ms is not None:
            q += " AND ts_ms < ?"
            params.append(end_ms)
        q += " ORDER BY ts_ms ASC"
        df = pd.read_sql_query(q, conn, params=params)
    finally:
        conn.close()
    if df.empty:
        return df
    # Drop residual duplicates defensively
    df = df.drop_duplicates(subset=["ts_ms"], keep="first").reset_index(drop=True)
    return df


def load_mark(
    db_path: Path,
    symbol: str,
    timeframe: str,
    start_ms: Optional[int] = None,
    end_ms: Optional[int] = None,
) -> pd.DataFrame:
    return load_ohlcv(db_path, symbol, timeframe, source="binance_mark", start_ms=start_ms, end_ms=end_ms)


def research_db() -> Path:
    return DATASETS / "research_ohlcv.sqlite"


def lockbox_db() -> Path:
    return DATASETS / "forward_lockbox_ohlcv.sqlite"


def load_funding(
    funding_db: Path,
    symbol: str,
    start_ms: Optional[int] = None,
    end_ms: Optional[int] = None,
) -> pd.DataFrame:
    if not funding_db.exists():
        return pd.DataFrame(columns=["funding_time_ms", "funding_rate"])
    conn = sqlite3.connect(str(funding_db))
    try:
        q = "SELECT funding_time_ms, funding_rate FROM funding WHERE symbol = ?"
        params: list = [symbol]
        if start_ms is not None:
            q += " AND funding_time_ms >= ?"
            params.append(start_ms)
        if end_ms is not None:
            q += " AND funding_time_ms < ?"
            params.append(end_ms)
        q += " ORDER BY funding_time_ms"
        return pd.read_sql_query(q, conn, params=params)
    finally:
        conn.close()
