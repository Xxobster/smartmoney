# Live parity — tsm-chandelier@BTCUSDT

Account: **Xxobster6**  
Pack: `tsm_chandelier_1h_btc_eth_sol_xxobster6_v1`  
Symbol: **BTCUSDT**  
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
| Signals | **100%** | Live-window signals filled, still open, or valid skip |
| Entries / exits | **100%** | Same side, bar, stop, target, exit reason |
| Fill prices | 99.9% | Live vs backtest fill (designed slip allowed, not a bug) |

## Verdict

- Candles match: True
- Indicator functions match: True
- Signal side / stop / target match: True
- Strategy working as specified: True
- Closed trades: 4  |  open: 0  |  live-window signals: 5
- Closed net profit and loss (USDT): **+4.1061**

## Closed trades

| Side | Live net | Live exit | Entry → exit (live) | Backtest entry → exit | 1-minute first touch | Levels match |
|---|---|---|---|---|---|---|
| short | -0.5385 | StopLoss | 63,766.7 → 64,243.3 | 63,715.1 → 64,240.6 (stop) | StopLoss | yes |
| long | +1.2975 | TakeProfit | 64,787.8 → 66,157.3 | 64,889.8 → 66,149.1 (target) | TakeProfit | yes |
| long | +5.6029 | TakeProfit | 71,522.0 → 77,216.1 | 71,596.3 → 77,222.4 (target) | TakeProfit | yes |
| long | -2.2558 | StopLoss | 78,833.4 → 76,663.1 | 79,308.6 → 76,666.9 (stop) | StopLoss | yes |

## Open trades

None.

## Live-window signals

| Entry UTC | Side | Stop | Target | Live action |
|---|---|---|---|---|
| 2026-08-11T15:00 | short | 64,240.6 | 62,266.2 | filled (closed) |
| 2026-08-19T13:00 | long | 64,426.7 | 66,149.1 | filled (closed) |
| 2026-08-19T15:00 | long | 65,203.3 | 67,972.4 | skipped (in_position) |
| 2026-08-20T09:00 | long | 69,673.3 | 77,222.4 | filled (closed) |
| 2026-08-21T09:00 | long | 76,666.9 | 87,075.2 | filled (closed) |

Designed fill gaps (not bugs): Bybit market entry vs Binance next-open + 0.05% slip; live Stop Loss / Take Profit market slip vs backtest fill at planned price.
