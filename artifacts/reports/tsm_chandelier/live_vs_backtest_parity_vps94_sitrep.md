# Live vs backtest parity — VPS 94 tsm_chandelier (2026-08-19)

- Generated: 2026-08-19T04:00:00+00:00
- Period: 2026-08-10T00:00:00+00:00 → now (since deploy)
- Maximum earned readiness: **LIVE_STOP / RESEARCH_ONLY**
- Evidence class: FORWARD_MICRO_LIVE_RECONCILE + RESEARCH_PROXY (Binance Last candles, Bybit fills)

## Verdict

- Indicator math research `signals.py` == live `signals_core.py`: **True**
- True backtest signals on **complete** Binance 1h == live fills: **True** (3/3)
- Gapped Virtual Private Server (VPS) shared database invented 3 extra shorts: **those were not real backtest entries**
- After backfill, shared 1h holes in the live window: **0**
- Units `tsm-chandelier@BTCUSDT|ETHUSDT|SOLUSDT`: **active** (restarted after the fix)

## What is live (this project / Xxobster6)

Only the authorized chandelier pack is live for this research line:

- `tsm-chandelier@BTCUSDT` active
- `tsm-chandelier@ETHUSDT` active
- `tsm-chandelier@SOLUSDT` active (exploratory Solana)

Same Virtual Private Server also runs other accounts (`tsm-vpa`, `llm2-pivot`, `xxobster2` screens). Those are not this pack.

## True backtest vs live (complete Binance 1h)

| Symbol | Side | Signal close (UTC) | Entry hour (UTC) | Stop | Target | Live fill | Slip vs close | Result |
|---|---|---|---|---|---|---|---|---|
| BTCUSDT | short | 2026-08-11 14:00 / 63747.0 | 15:00 | 64240.61 | 62266.16 | 63766.7 | ~3.1 basis points (fill slightly above close; good for a short) | Stop −0.538 |
| ETHUSDT | short | 2026-08-11 14:00 / 1872.67 | 15:00 | 1890.17 | 1820.16 | 1872.33 | ~1.8 basis points (fill slightly below close; small adverse for a short) | Stop −0.205 |
| SOLUSDT | short | 2026-08-16 21:00 / 74.30 | 22:00 | 74.80 | 72.79 | 74.13 | ~23 basis points adverse | Stop −0.075 |

No open trades now. Live took every complete-history signal and no extras.

## False signals from candle holes (not backtest)

Shared database was missing ~10 hours (Ethereum/Solana on 12 Aug) and ~43 hours (all three, 13–14 Aug). Average True Range (ATR) and the 50-period Exponential Moving Average (EMA) jumped across the hole and invented:

- ETHUSDT short 2026-08-13 00:00
- SOLUSDT short 2026-08-13 00:00
- BTCUSDT short 2026-08-15 00:00

Those **do not exist** on continuous Binance 1h. Live did not fill them (collector was behind / late). After backfill they disappear.

## VPS correction applied (authorized)

1. Backfilled Binance 1h holes in `/var/lib/botsgeneral/shared_candles.db` (last 800 closed hours).
2. Bot now fetches the just-closed 1h bar from Binance REST if the collector is late.
3. A later `stale_entry` skip no longer overwrites a real fill in `handled_entries`.
4. Restarted the three chandelier units — bootstrap clean, collector active.

## Principal blockers (unchanged readiness)

- Historical `SHADOW_READY` is not upgraded by 3 micro-live stops.
- Evidence remains RESEARCH_PROXY (Binance signal candles vs Bybit execution).
- Account margin mode is cross, not isolated.
- `set_trading_stop` 34040 after the first Bitcoin/Ethereum fills — protective orders were sent on the entry ticket; verify on the exchange if it happens again.
- Collector previously had a multi-day 1h hole; keep `botsgeneral-collector@94.156.189.76` watched.
