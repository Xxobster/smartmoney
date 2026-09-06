# Live parity — account Xxobster6

Pack: `tsm_chandelier_1h_btc_eth_sol_xxobster6_v1`  
Bots: `tsm-chandelier@BTCUSDT`, `tsm-chandelier@ETHUSDT`, `tsm-chandelier@SOLUSDT`  
Generated: 2026-08-25T12:16:34.624994+00:00

Maximum earned readiness: **LIVE_STOP / RESEARCH_ONLY**  
Evidence class: FORWARD_MICRO_LIVE_RECONCILE + RESEARCH_PROXY

Principal blocker: Live is taking the same 1h chandelier signals (side, stop, target, min size) as the research function. Fill prices and exit times differ by design (Bybit market slip vs Binance next-open + 0.05% entry slip, zero exit slip in backtest). Historical freeze remains SHADOW_READY; this micro-live window is not a new gate pass.

Historical freeze: LIVE_STOP / SHADOW_READY (BTC+ETH 1h, artifacts/reports/tsm_chandelier/1h_SHADOW_FREEZE.json)

## Closeness (account mean)

| Aspect | Score | What it measures |
|---|---|---|
| Candles | **100%** | Overlapping 1-hour Open-High-Low-Close equal |
| Calculations | **100%** | Average True Range / Exponential Moving Average / stop / target |
| Signals | **85%** | Live-window signals filled, still open, or valid skip |
| Entries / exits | **96.8%** | Same side, bar, stop, target, exit reason |
| Fill prices | 99.8% | Live vs backtest fill (designed slip allowed, not a bug) |

## Rollup

- Closed trades: 11  |  open: 0
- Closed net profit and loss (USDT): **+7.5479**
- Strategy working as specified: True
- Material logic bug: False

## Per bot

| Bot | Symbol | Candles | Calculations | Signals | Entries/exits | Fill prices | Closed net USDT |
|---|---|---|---|---|---|---|---|
| `tsm-chandelier@BTCUSDT` | BTCUSDT | 100% | 100% | 100% | 100% | 99.9% | +4.1061 |
| `tsm-chandelier@ETHUSDT` | ETHUSDT | 100% | 100% | 75% | 94.4% | 99.7% | +2.3090 |
| `tsm-chandelier@SOLUSDT` | SOLUSDT | 100% | 100% | 80% | 95.8% | 99.9% | +1.1328 |

Solana is exploratory and is not inside the frozen Bitcoin + Ethereum Shadow-ready claim.
