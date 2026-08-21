#!/usr/bin/env python3
"""One-shot: fill Binance 1h holes in shared_candles.db (closed bars only)."""

from __future__ import annotations

from botsgeneral.db import CandleDB
from botsgeneral.fetch import binance_rest
from botsgeneral.models import CandlePair

DB = "/var/lib/botsgeneral/shared_candles.db"
SYMBOLS = ("BTCUSDT", "ETHUSDT", "SOLUSDT")


def main() -> None:
    db = CandleDB(DB)
    for sym in SYMBOLS:
        pair = CandlePair(exchange="binance", symbol=sym, timeframe="1h")
        n = binance_rest.upsert_pair(db, pair, limit=800)
        print(f"{sym} upserted_tip_window={n}")


if __name__ == "__main__":
    main()
