# Live parity — tsm-chandelier@ETHUSDT

Account: **Xxobster6**  
Pack: `tsm_chandelier_1h_btc_eth_sol_xxobster6_v1`  
Symbol: **ETHUSDT**  
Freeze role: inside historical SHADOW_READY freeze (Bitcoin + Ethereum 1h)

Maximum earned readiness: **LIVE_STOP / RESEARCH_ONLY**  
Evidence class: FORWARD_MICRO_LIVE_RECONCILE + RESEARCH_PROXY  
Generated: 2026-08-25T12:16:34.624994+00:00

Principal blocker: Live is taking the same 1h chandelier signals (side, stop, target, min size) as the research function. Fill prices and exit times differ by design (Bybit market slip vs Binance next-open + 0.05% entry slip, zero exit slip in backtest). Historical freeze remains SHADOW_READY; this micro-live window is not a new gate pass.

## Closeness (live vs backtest)

| Aspect | Score | What it measures |
|---|---|---|
| Candles | **100%** | Overlapping 1-hour Open-High-Low-Close equal |
| Calculations | **100%** | Average True Range / Exponential Moving Average / stop / target |
| Signals | **75%** | Live-window signals filled, still open, or valid skip |
| Entries / exits | **94.4%** | Same side, bar, stop, target, exit reason |
| Fill prices | 99.7% | Live vs backtest fill (designed slip allowed, not a bug) |

## Verdict

- Candles match: True
- Indicator functions match: True
- Signal side / stop / target match: True
- Strategy working as specified: True
- Closed trades: 3  |  open: 0  |  live-window signals: 4
- Closed net profit and loss (USDT): **+2.3090**

## Closed trades

| Side | Live net | Live exit | Entry → exit (live) | Backtest entry → exit | 1-minute first touch | Levels match |
|---|---|---|---|---|---|---|
| short | -0.2051 | StopLoss | 1,872.3 → 1,891.0 | 1,871.7 → 1,890.2 (stop) | StopLoss | yes |
| long | +0.7252 | TakeProfit | 1,970.7 → 2,045.4 | 1,970.9 → 2,045.1 (target_entry_bar) | TakeProfit | yes |
| long | +1.7889 | TakeProfit | 2,220.1 → 2,402.6 | 2,219.2 → 2,444.9 (max_hold) | TakeProfit | yes |

## Open trades

None.

## Live-window signals

| Entry UTC | Side | Stop | Target | Live action |
|---|---|---|---|---|
| 2026-08-11T15:00 | short | 1,890.2 | 1,820.2 | filled (closed) |
| 2026-08-19T15:00 | long | 1,944.8 | 2,045.1 | filled (closed) |
| 2026-08-19T21:00 | long | 2,137.2 | 2,460.5 | see live database |
| 2026-08-21T09:00 | long | 2,368.2 | 2,674.8 | skipped (in_position) |

Designed fill gaps (not bugs): Bybit market entry vs Binance next-open + 0.05% slip; live Stop Loss / Take Profit market slip vs backtest fill at planned price.
