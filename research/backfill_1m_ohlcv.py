#!/usr/bin/env python3
"""Backfill Binance USDT-M 1-minute bars into research_ohlcv.sqlite.

Uses data.binance.vision monthly/daily zip files. The REST kline host
(fapi.binance.com) is often unreachable from this machine.

EXEC-021 needs 1-minute touch data on the *same* calendar as the decision bars.
"""

from __future__ import annotations

import io
import sqlite3
import time
import urllib.error
import urllib.request
import zipfile
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DB = ROOT / "artifacts" / "datasets" / "research_ohlcv.sqlite"
SYMBOLS = ("BTCUSDT", "ETHUSDT", "SOLUSDT")
VISION = "https://data.binance.vision/data/futures/um"
STEP = 60_000
START = datetime(2020, 1, 1, tzinfo=timezone.utc)
STEP = 60_000


def utc(ms: int | None) -> str | None:
    if ms is None:
        return None
    return datetime.fromtimestamp(ms / 1000, timezone.utc).isoformat()


def span(con: sqlite3.Connection, symbol: str) -> tuple[int | None, int | None]:
    row = con.execute(
        """
        SELECT MIN(ts_ms), MAX(ts_ms) FROM market_ohlcv
        WHERE source='binance' AND symbol=? AND timeframe='1m' AND is_complete=1
        """,
        (symbol,),
    ).fetchone()
    lo = int(row[0]) if row and row[0] is not None else None
    hi = int(row[1]) if row and row[1] is not None else None
    return lo, hi


def month_count(con: sqlite3.Connection, symbol: str, start_ms: int, end_ms: int) -> int:
    row = con.execute(
        """
        SELECT COUNT(*) FROM market_ohlcv
        WHERE source='binance' AND symbol=? AND timeframe='1m' AND is_complete=1
          AND ts_ms>=? AND ts_ms<?
        """,
        (symbol, start_ms, end_ms),
    ).fetchone()
    return int(row[0] or 0)


def upsert_frame(con: sqlite3.Connection, symbol: str, frame: pd.DataFrame) -> int:
    if frame.empty:
        return 0
    now = int(time.time() * 1000)
    ts = frame["ts_ms"].to_numpy(np.int64)
    rows = list(
        zip(
            ["binance"] * len(frame),
            [symbol] * len(frame),
            ["1m"] * len(frame),
            ts.tolist(),
            frame["open"].to_numpy(float).tolist(),
            frame["high"].to_numpy(float).tolist(),
            frame["low"].to_numpy(float).tolist(),
            frame["close"].to_numpy(float).tolist(),
            frame["volume"].to_numpy(float).tolist(),
            ["last"] * len(frame),
            [1] * len(frame),
            [now] * len(frame),
            ["usdt_perp"] * len(frame),
            [VISION] * len(frame),
        )
    )
    con.executemany(
        """
        INSERT OR REPLACE INTO market_ohlcv
        (source, symbol, timeframe, ts_ms, open, high, low, close, volume,
         price_type, is_complete, downloaded_at, product, source_endpoint)
        VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)
        """,
        rows,
    )
    con.commit()
    return len(rows)


def fetch_zip(url: str) -> bytes | None:
    try:
        with urllib.request.urlopen(url, timeout=120) as resp:
            if resp.status != 200:
                return None
            return resp.read()
    except urllib.error.HTTPError as exc:
        if exc.code == 404:
            return None
        raise


def parse_klines_zip(raw: bytes) -> pd.DataFrame:
    with zipfile.ZipFile(io.BytesIO(raw)) as zf:
        name = zf.namelist()[0]
        with zf.open(name) as fh:
            df = pd.read_csv(
                fh,
                header=None,
                usecols=[0, 1, 2, 3, 4, 5],
                names=["ts_ms", "open", "high", "low", "close", "volume"],
            )
    ts = pd.to_numeric(df["ts_ms"], errors="coerce")
    df = df.loc[ts.notna()].copy()
    df["ts_ms"] = ts.loc[df.index].astype("int64")
    for col in ("open", "high", "low", "close", "volume"):
        df[col] = pd.to_numeric(df[col], errors="coerce")
    return df.dropna()


def month_starts(start: datetime, end: datetime) -> list[datetime]:
    out: list[datetime] = []
    y, m = start.year, start.month
    while datetime(y, m, 1, tzinfo=timezone.utc) < end:
        out.append(datetime(y, m, 1, tzinfo=timezone.utc))
        if m == 12:
            y, m = y + 1, 1
        else:
            m += 1
    return out


def ingest_url(con: sqlite3.Connection, symbol: str, url: str) -> int:
    raw = fetch_zip(url)
    if raw is None:
        return 0
    frame = parse_klines_zip(raw)
    return upsert_frame(con, symbol, frame)


def backfill_symbol(con: sqlite3.Connection, symbol: str) -> int:
    now = datetime.now(timezone.utc)
    this_month = datetime(now.year, now.month, 1, tzinfo=timezone.utc)
    wrote = 0
    for start in month_starts(START, this_month):
        if start.month == 12:
            end = datetime(start.year + 1, 1, 1, tzinfo=timezone.utc)
        else:
            end = datetime(start.year, start.month + 1, 1, tzinfo=timezone.utc)
        start_ms = int(start.timestamp() * 1000)
        end_ms = int(end.timestamp() * 1000)
        have = month_count(con, symbol, start_ms, end_ms)
        expected = max(1, (end_ms - start_ms) // STEP)
        if have >= int(expected * 0.99):
            print(symbol, start.strftime("%Y-%m"), "skip have", have, flush=True)
            continue
        url = (
            f"{VISION}/monthly/klines/{symbol}/1m/"
            f"{symbol}-1m-{start.strftime('%Y-%m')}.zip"
        )
        n = ingest_url(con, symbol, url)
        wrote += n
        print(symbol, start.strftime("%Y-%m"), "wrote", n, "had", have, flush=True)
        time.sleep(0.05)

    # Current month + a few daily files so the last incomplete month is filled.
    day = this_month
    while day < now:
        url = (
            f"{VISION}/daily/klines/{symbol}/1m/"
            f"{symbol}-1m-{day.strftime('%Y-%m-%d')}.zip"
        )
        n = ingest_url(con, symbol, url)
        if n:
            wrote += n
            print(symbol, day.strftime("%Y-%m-%d"), "daily wrote", n, flush=True)
        day = datetime.fromtimestamp(day.timestamp() + 86400, timezone.utc)
        time.sleep(0.03)
    return wrote


def main() -> None:
    con = sqlite3.connect(str(DB))
    con.execute("PRAGMA journal_mode=WAL")
    total = 0
    for sym in SYMBOLS:
        lo, hi = span(con, sym)
        print(sym, "existing 1m", utc(lo), "->", utc(hi), flush=True)
        total += backfill_symbol(con, sym)
        lo, hi = span(con, sym)
        print(sym, "now 1m", utc(lo), "->", utc(hi), flush=True)
    con.close()
    print("done total_rows", total, flush=True)


if __name__ == "__main__":
    main()
