#!/usr/bin/env python3
"""Run tsm_chandelier live bot for one symbol (Bybit + botsgeneral shared candles)."""

from __future__ import annotations

import argparse
import logging
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from chand.live.bot import ChandLiveBot  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description="tsm_chandelier live bot (Bybit)")
    parser.add_argument("--symbol", required=True, help="e.g. BTCUSDT")
    parser.add_argument(
        "--pack",
        default=str(ROOT / "configs" / "live_btc_eth_sol_1h_xxobster6.json"),
    )
    parser.add_argument("--account", default="", help="Override account name in api_keys.json")
    parser.add_argument("--keys", default="", help="Path to api_keys.json")
    parser.add_argument("--state-db", default="", help="Shared state sqlite path")
    parser.add_argument("--dry-run", action="store_true", help="Log signals without placing orders")
    parser.add_argument("--poll-sec", type=int, default=0, help="Override pack poll_sec")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    bot = ChandLiveBot(
        args.symbol,
        pack_path=args.pack,
        account=args.account or None,
        state_db=args.state_db or None,
        keys_path=args.keys or None,
        dry_run=True if args.dry_run else None,
    )
    if args.poll_sec > 0:
        bot.poll_sec = args.poll_sec
        bot.idle_poll_sec = float(args.poll_sec)
    if os.environ.get("TSM_CHANDELIER_DRY_RUN", "").lower() in ("1", "true", "yes"):
        bot.dry_run = True
    bot.run()


if __name__ == "__main__":
    main()
