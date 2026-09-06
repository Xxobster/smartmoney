# Live vs backtest — tsm_chandelier VPS94 — 2026-08-21 04:28 UTC

Maximum earned readiness: **LIVE_STOP / RESEARCH_ONLY**  
Evidence class: **FORWARD_MICRO_LIVE_RECONCILE + RESEARCH_PROXY**  
Principal blocker: live and backtest fills are not identical by design (Bybit market slip vs Binance next-open + 0.05% entry slip, zero exit slip in the backtester). No material strategy-logic mismatch was found. Historical freeze remains `LIVE_STOP / SHADOW_READY` (Bitcoin + Ethereum 1h). This micro-live window is not a new gate pass. Do not raise size.

## Scope

Only this project's live bots: `tsm-chandelier@BTCUSDT|ETHUSDT|SOLUSDT` on VPS 94 (all active). Smart Money Concepts (SMC) is not deployed.

Candles (this run): local Binance 1-hour through **2026-08-21 03:00 UTC**, 1-minute through **04:27 UTC**, imported into `artifacts/datasets/research_ohlcv.sqlite`.

## Checks

| Layer | Result |
|---|---|
| VPS shared 1h vs research 1h vs fresh Binance 1h | Open/high/low/close match on overlap |
| Average True Range (ATR), Exponential Moving Average 50 (EMA50), bands, chandelier stop/target | Research `signals.py` == live `signals_core.py` |
| Live code vs VPS `/opt/tsm-chandelier` | `bot.py`, `state.py`, `signals_core.py` hashes match |
| Every live-window 1h signal | Taken or correctly skipped (`BTCUSDT` 15:00 19 Aug `in_position`) |
| Closed trades (7) | Same side, stop, target, min quantity, entry hour, stop vs take-profit reason |
| Open trades (3) | 1-minute path has not touched stop or target; backtest still open (`end_of_data`) |

## Closed trades (live vs 1-minute backtest)

| Pair | Side | Live net | Live exit | 1m first touch | Same signal levels |
|---|---|---|---|---|---|
| ETHUSDT | short | −0.205 | StopLoss 12 Aug 04:21 | StopLoss 04:21 | yes |
| BTCUSDT | short | −0.538 | StopLoss 12 Aug 12:04 | StopLoss 12:08 | yes |
| SOLUSDT | short | −0.075 | StopLoss 17 Aug 01:01 | StopLoss 01:01 | yes |
| SOLUSDT | long | +0.257 | TakeProfit 19 Aug 14:58 | TakeProfit 14:58 | yes |
| BTCUSDT | long | +1.297 | TakeProfit 19 Aug 15:05 | TakeProfit 15:05 | yes |
| ETHUSDT | long | +0.725 | TakeProfit 19 Aug 15:26 | TakeProfit 15:26 | yes |
| SOLUSDT | long | +0.484 | TakeProfit 19 Aug 21:06 | TakeProfit 21:06 | yes |

Fill prices differ (expected). Quantity matched min size on all seven.

Open longs as of 2026-08-21 04:27 UTC (1-minute last vs planned stop / take-profit): Ethereum 2345 vs 2137 / 2460; Solana 89.02 vs 83.57 / 95.82; Bitcoin 74802 vs 69673 / 77222. None touched. Backtest still open (`end_of_data`).

JSON: `artifacts/reports/tsm_chandelier/live_vs_bt_full_latest.json`

## Is the strategy working as specified?

Yes on logic. Live is executing the frozen 1h chandelier rules (ATR-band break, chandelier stop, EMA50 filter, max hold 36, min size). Historical outer out-of-sample (OOS) freeze is profitable (pooled profit factor 1.56, 394 trades, Bitcoin+Ethereum). Micro-live is too small to confirm or deny that edge. Full-history last-six-month research prints were negative; that does not authorize a retune.

## Fixes

No strategy change. Designed execution gaps were not “fixed” (changing live to limit exits, or adding exit slip into the frozen backtester, would rewrite the economic test after seeing results).

A previous `handled_entries` overwrite (`stale_entry` replacing a fill) is already guarded in current `state.py`; VPS hash matches local. First August 11/16 rows in the live database remain historically dirty but do not change current behavior.

JSON: `artifacts/reports/tsm_chandelier/live_vs_bt_full_latest.json`
