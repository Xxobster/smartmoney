"""Copy SOLUSDT OHLCV from shared candles DB into smartmoney research DB."""

from __future__ import annotations

import sqlite3
import time
from pathlib import Path

SRC = Path(r"D:\projectsdata\candles\market_ohlcv.sqlite")
DST = Path(r"D:\projects\smartmoney\artifacts\datasets\research_ohlcv.sqlite")
SYMBOL = "SOLUSDT"
CUT_MS = 1_776_589_200_000  # match research meta cut_ms
# 1m only from a bit before first outer OOS (2023-11-01) to keep import light
ONE_M_START_MS = 1_698_000_000_000


def _copy(src: sqlite3.Connection, dst: sqlite3.Connection, *, source: str, tf: str, start_ms: int | None = None) -> int:
    cols = [
        "source",
        "symbol",
        "timeframe",
        "ts_ms",
        "open",
        "high",
        "low",
        "close",
        "volume",
        "price_type",
        "is_complete",
        "downloaded_at",
        "product",
        "source_endpoint",
    ]
    col_sql = ", ".join(cols)
    q = (
        f"select {col_sql} from market_ohlcv "
        f"where source=? and symbol=? and timeframe=? and ts_ms < ?"
    )
    params: list = [source, SYMBOL, tf, CUT_MS]
    if start_ms is not None:
        q += " and ts_ms >= ?"
        params.append(start_ms)
    rows = src.execute(q, params).fetchall()
    if not rows:
        print(f"  {source} {tf}: 0 rows")
        return 0
    # force complete + downloaded_at if null
    fixed = []
    now = int(time.time() * 1000)
    for r in rows:
        r = list(r)
        if r[10] is None:
            r[10] = 1
        if r[11] is None:
            r[11] = now
        fixed.append(tuple(r))
    dst.executemany(
        f"insert or ignore into market_ohlcv ({col_sql}) values ({','.join('?'*len(cols))})",
        fixed,
    )
    dst.commit()
    n = dst.execute(
        "select count(*) from market_ohlcv where source=? and symbol=? and timeframe=? and is_complete=1",
        (source, SYMBOL, tf),
    ).fetchone()[0]
    print(f"  {source} {tf}: wrote {len(fixed)} -> complete_rows={n}")
    return n


def main() -> None:
    src = sqlite3.connect(str(SRC))
    dst = sqlite3.connect(str(DST))
    try:
        print("Import SOLUSDT into", DST)
        _copy(src, dst, source="binance", tf="1h")
        _copy(src, dst, source="binance_mark", tf="1h")
        _copy(src, dst, source="binance", tf="1m", start_ms=ONE_M_START_MS)
        # refresh meta symbols list
        cur = dst.execute("select value from meta where key='symbols'").fetchone()
        if cur:
            syms = [s.strip() for s in str(cur[0]).split(",") if s.strip()]
            if SYMBOL not in syms:
                syms.append(SYMBOL)
                dst.execute(
                    "insert or replace into meta(key, value) values ('symbols', ?)",
                    (",".join(syms),),
                )
        dst.execute(
            "insert or replace into meta(key, value) values ('import_solusdt', ?)",
            (f"from={SRC}; cut_ms={CUT_MS}; 1m_from={ONE_M_START_MS}",),
        )
        dst.commit()
        print("meta symbols", dst.execute("select value from meta where key='symbols'").fetchone())
    finally:
        src.close()
        dst.close()
    print("done")


if __name__ == "__main__":
    main()
