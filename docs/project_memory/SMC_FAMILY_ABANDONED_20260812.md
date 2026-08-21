# Generation note — after SMC abandon (2026-08-12)

## Abandoned line
`smc_confluence_retrace` / killzone Gen1–Gen4 on BTCUSDT+ETHUSDT 5m via tradesim.

Reason: Gen2 and Gen4 July OOS claims fail exact re-run on today’s path (both net negative, PF << 1). Invert diagnostic also loses. Non-reproducible “winners” are not live candidates.

## Do not
- Retune Gen2–4 on viewed OOS
- Deploy any SMC Gen* freeze
- Treat mean-of-symbol Sharpe/PF from old reports as evidence

## Next research (must be newly preregistered before any OOS)
Choose a **different** economic hypothesis, for example:
1. Continue / harden **tsm_chandelier** (already micro-live) with Bybit-native data + green conformance + liquidation tiers, or
2. A new sparse higher-timeframe family with a written rationale and frozen search space **before** search.

No Gen5 search space is frozen yet — wait for explicit hypothesis choice before Optuna/OOS.
