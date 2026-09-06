# Live parity — tsm-chandelier@SOLUSDT

Account: **Xxobster6**  
Pack: `tsm_chandelier_1h_btc_eth_sol_xxobster6_v1`  
Symbol: **SOLUSDT**  
Freeze role: exploratory - not in the frozen Bitcoin + Ethereum claim

Maximum earned readiness: **LIVE_STOP / RESEARCH_ONLY**  
Evidence class: FORWARD_MICRO_LIVE_RECONCILE + RESEARCH_PROXY  
Generated: 2026-08-25T12:16:34.624994+00:00

Principal blocker: Live is taking the same 1h chandelier signals (side, stop, target, min size) as the research function. Fill prices and exit times differ by design (Bybit market slip vs Binance next-open + 0.05% entry slip, zero exit slip in backtest). Historical freeze remains SHADOW_READY; this micro-live window is not a new gate pass.

## Closeness (live vs backtest)

| Aspect | Score | What it measures |
|---|---|---|
| Candles | **100%** | Overlapping 1-hour Open-High-Low-Close equal |
| Calculations | **100%** | Average True Range / Exponential Moving Average / stop / target |
| Signals | **80%** | Live-window signals filled, still open, or valid skip |
| Entries / exits | **95.8%** | Same side, bar, stop, target, exit reason |
| Fill prices | 99.9% | Live vs backtest fill (designed slip allowed, not a bug) |

## Verdict

- Candles match: True
- Indicator functions match: True
- Signal side / stop / target match: True
- Strategy working as specified: True
- Closed trades: 4  |  open: 0  |  live-window signals: 5
- Closed net profit and loss (USDT): **+1.1328**

## Closed trades

| Side | Live net | Live exit | Entry → exit (live) | Backtest entry → exit | 1-minute first touch | Levels match |
|---|---|---|---|---|---|---|
| short | -0.0751 | StopLoss | 74.13 → 74.80 | 74.25 → 74.80 (stop) | StopLoss | yes |
| long | +0.2572 | TakeProfit | 78.28 → 80.94 | 78.41 → 80.95 (target) | TakeProfit | yes |
| long | +0.4837 | TakeProfit | 80.91 → 85.84 | 80.89 → 85.88 (target) | TakeProfit | yes |
| long | +0.4668 | TakeProfit | 86.55 → 91.36 | 86.68 → 91.67 (max_hold) | TakeProfit | yes |

## Open trades

None.

## Live-window signals

| Entry UTC | Side | Stop | Target | Live action |
|---|---|---|---|---|
| 2026-08-16T22:00 | short | 74.80 | 72.79 | filled (closed) |
| 2026-08-19T13:00 | long | 77.51 | 80.95 | filled (closed) |
| 2026-08-19T15:00 | long | 79.16 | 85.88 | filled (closed) |
| 2026-08-19T22:00 | long | 83.57 | 95.82 | see live database |
| 2026-08-21T09:00 | long | 89.96 | 103.28 | skipped (in_position) |

Designed fill gaps (not bugs): Bybit market entry vs Binance next-open + 0.05% slip; live Stop Loss / Take Profit market slip vs backtest fill at planned price.
