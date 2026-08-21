"""Build TWO physical SQLite datasets: research + chronologically-last forward lockbox.

Uses SQL ATTACH + INSERT SELECT (no giant pandas load). Features must later be
computed SEPARATELY on each file (no cross-fit).
"""
from __future__ import annotations

import argparse
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, Sequence

import yaml

from paths import CONFIG_DIR, DATASETS, DEFAULT_CANDLES_DB, ensure_artifact_dirs

SCHEMA = """
CREATE TABLE IF NOT EXISTS market_ohlcv (
  source TEXT NOT NULL,
  symbol TEXT NOT NULL,
  timeframe TEXT NOT NULL,
  ts_ms INTEGER NOT NULL,
  open REAL NOT NULL,
  high REAL NOT NULL,
  low REAL NOT NULL,
  close REAL NOT NULL,
  volume REAL,
  price_type TEXT,
  is_complete INTEGER NOT NULL DEFAULT 1,
  downloaded_at INTEGER NOT NULL,
  product TEXT,
  source_endpoint TEXT,
  PRIMARY KEY (source, symbol, timeframe, ts_ms)
);
CREATE INDEX IF NOT EXISTS idx_market_lookup
  ON market_ohlcv(symbol, timeframe, ts_ms);
CREATE TABLE IF NOT EXISTS meta (
  key TEXT PRIMARY KEY,
  value TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS qa_rejects (
  source TEXT,
  symbol TEXT,
  timeframe TEXT,
  ts_ms INTEGER,
  reason TEXT,
  PRIMARY KEY (source, symbol, timeframe, ts_ms, reason)
);
"""


def _load_yaml(name: str) -> dict:
    with open(CONFIG_DIR / name, encoding="utf-8") as f:
        return yaml.safe_load(f)


def _init_db(path: Path) -> sqlite3.Connection:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        path.unlink()
    conn = sqlite3.connect(str(path))
    conn.executescript(SCHEMA)
    return conn


def set_meta(conn: sqlite3.Connection, mapping: dict) -> None:
    for k, v in mapping.items():
        conn.execute(
            "INSERT OR REPLACE INTO meta(key, value) VALUES (?, ?)",
            (k, str(v)),
        )
    conn.commit()


def _in_clause(n: int) -> str:
    return ",".join("?" * n)


def build_datasets(
    src_db: Optional[Path] = None,
    symbols: Optional[Sequence[str]] = None,
    lockbox_days: Optional[int] = None,
) -> tuple[Path, Path]:
    ensure_artifact_dirs()
    profile = _load_yaml("project_profile.yaml")
    search = _load_yaml("search_space.yaml")
    src_db = Path(src_db or profile.get("market_database") or DEFAULT_CANDLES_DB)
    symbols = list(symbols or profile.get("primary_research_symbols") or ["BTCUSDT", "ETHUSDT"])
    lockbox_days = int(lockbox_days or search.get("forward_lockbox_days") or 90)
    timeframes = list(profile.get("strategy_timeframes") or ["1d", "4h", "1h", "15m", "5m"])
    if profile.get("include_1m_in_datasets") and profile.get("execution_replay_timeframe"):
        tf = profile["execution_replay_timeframe"]
        if tf not in timeframes:
            timeframes.append(tf)
    sources = ["binance", "binance_mark"]

    research_start = search.get("research_start_utc", "2020-01-01T00:00:00Z")
    start_dt = datetime.fromisoformat(research_start.replace("Z", "+00:00"))
    start_ms = int(start_dt.timestamp() * 1000)

    src = sqlite3.connect(f"file:{src_db.as_posix()}?mode=ro", uri=True)
    try:
        last_ms = src.execute(
            f"""
            SELECT MAX(ts_ms) FROM market_ohlcv
            WHERE source='binance' AND timeframe='1h'
              AND symbol IN ({_in_clause(len(symbols))})
            """,
            symbols,
        ).fetchone()[0]
        if last_ms is None:
            raise RuntimeError(f"No candles found in {src_db} for {symbols}")
        cut_ms = int(last_ms) - lockbox_days * 86_400_000
        print(f"Source OK. last_ms={last_ms} cut_ms={cut_ms}")
    finally:
        src.close()

    research_path = DATASETS / "research_ohlcv.sqlite"
    lockbox_path = DATASETS / "forward_lockbox_ohlcv.sqlite"
    rconn = _init_db(research_path)
    lconn = _init_db(lockbox_path)

    try:
        rconn.execute(f"ATTACH DATABASE '{src_db.as_posix()}' AS src")
        lconn.execute(f"ATTACH DATABASE '{src_db.as_posix()}' AS src")

        params = list(sources) + list(symbols) + list(timeframes)

        # Copy research range with QA filters inline
        print("Copying research slice...")
        rconn.execute(
            f"""
            INSERT INTO market_ohlcv
            SELECT source, symbol, timeframe, ts_ms, open, high, low, close, volume,
                   price_type, is_complete, downloaded_at, product, source_endpoint
            FROM src.market_ohlcv
            WHERE source IN ({_in_clause(len(sources))})
              AND symbol IN ({_in_clause(len(symbols))})
              AND timeframe IN ({_in_clause(len(timeframes))})
              AND ts_ms >= ? AND ts_ms < ?
              AND is_complete = 1
              AND open > 0 AND high > 0 AND low > 0 AND close > 0
              AND high >= low
              AND high >= open AND high >= close
              AND low <= open AND low <= close
            """,
            params + [start_ms, cut_ms],
        )
        # Rejects
        rconn.execute(
            f"""
            INSERT OR IGNORE INTO qa_rejects(source, symbol, timeframe, ts_ms, reason)
            SELECT source, symbol, timeframe, ts_ms, 'invalid_ohlc'
            FROM src.market_ohlcv
            WHERE source IN ({_in_clause(len(sources))})
              AND symbol IN ({_in_clause(len(symbols))})
              AND timeframe IN ({_in_clause(len(timeframes))})
              AND ts_ms >= ? AND ts_ms < ?
              AND (
                open <= 0 OR high <= 0 OR low <= 0 OR close <= 0
                OR high < low OR high < open OR high < close
                OR low > open OR low > close
              )
            """,
            params + [start_ms, cut_ms],
        )
        rconn.commit()
        print("Copying lockbox slice...")
        lconn.execute(
            f"""
            INSERT INTO market_ohlcv
            SELECT source, symbol, timeframe, ts_ms, open, high, low, close, volume,
                   price_type, is_complete, downloaded_at, product, source_endpoint
            FROM src.market_ohlcv
            WHERE source IN ({_in_clause(len(sources))})
              AND symbol IN ({_in_clause(len(symbols))})
              AND timeframe IN ({_in_clause(len(timeframes))})
              AND ts_ms >= ? AND ts_ms <= ?
              AND is_complete = 1
              AND open > 0 AND high > 0 AND low > 0 AND close > 0
              AND high >= low
              AND high >= open AND high >= close
              AND low <= open AND low <= close
            """,
            params + [cut_ms, int(last_ms)],
        )
        lconn.commit()

        rconn.execute("DETACH DATABASE src")
        lconn.execute("DETACH DATABASE src")

        r_rows = rconn.execute("SELECT COUNT(*) FROM market_ohlcv").fetchone()[0]
        l_rows = lconn.execute("SELECT COUNT(*) FROM market_ohlcv").fetchone()[0]
        r_rej = rconn.execute("SELECT COUNT(*) FROM qa_rejects").fetchone()[0]

        # Overlap check
        rconn.execute(f"ATTACH DATABASE '{lockbox_path.as_posix()}' AS lb")
        overlap_n = rconn.execute(
            """
            SELECT COUNT(*) FROM market_ohlcv r
            JOIN lb.market_ohlcv l
              ON r.source=l.source AND r.symbol=l.symbol
             AND r.timeframe=l.timeframe AND r.ts_ms=l.ts_ms
            """
        ).fetchone()[0]
        rconn.execute("DETACH DATABASE lb")
        assert int(overlap_n) == 0, f"Research/lockbox overlap rows: {overlap_n}"

        common = {
            "source_db": str(src_db),
            "symbols": ",".join(symbols),
            "timeframes": ",".join(timeframes),
            "sources": ",".join(sources),
            "cut_ms": cut_ms,
            "cut_utc": datetime.fromtimestamp(cut_ms / 1000, tz=timezone.utc).isoformat(),
            "last_ms": last_ms,
            "lockbox_days": lockbox_days,
            "built_utc": datetime.now(timezone.utc).isoformat(),
            "utc_semantics": "ts_ms is UTC epoch milliseconds candle open",
            "qa_policy": "reject_invalid_never_fill",
        }
        set_meta(
            rconn,
            {
                **common,
                "dataset_role": "research",
                "range": f"[{start_ms}, {cut_ms})",
                "rows": r_rows,
                "rejects": r_rej,
            },
        )
        set_meta(
            lconn,
            {
                **common,
                "dataset_role": "forward_lockbox",
                "range": f"[{cut_ms}, {last_ms}]",
                "rows": l_rows,
                "rejects": 0,
            },
        )
    finally:
        rconn.close()
        lconn.close()

    print(f"Research DB -> {research_path} rows={r_rows} rejects={r_rej}")
    print(f"Lockbox  DB -> {lockbox_path} rows={l_rows}")
    print(f"Cut UTC: {datetime.fromtimestamp(cut_ms / 1000, tz=timezone.utc).isoformat()}")
    return research_path, lockbox_path


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--src-db", type=str, default=None)
    p.add_argument("--symbols", nargs="+", default=None)
    p.add_argument("--lockbox-days", type=int, default=None)
    args = p.parse_args()
    build_datasets(args.src_db, args.symbols, args.lockbox_days)


if __name__ == "__main__":
    main()
