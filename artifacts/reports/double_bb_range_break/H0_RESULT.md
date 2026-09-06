# Double Bollinger inner-range breakout — hypothesis-0

| Field | Value |
|-------|--------|
| **Maximum earned readiness** | `LIVE_STOP / RESEARCH_ONLY` |
| **Evidence class** | `EXPLORATORY_IN_SAMPLE` (full-history Hypothesis-0, not a 2027-style exam). Data: `RESEARCH_PROXY` (contaminated; engine stamp NOT GREEN) |
| **Principal blocker** | Profit Factor (PF) 0.49–0.81 on all eight legs. ~120 trades/month on 15-minute; fees and slippage dominate. |
| **Live-test candidate?** | **No** |

Source: `0cn9mAnOoX0` breakout method. Ranging = prior close inside 0.5-sigma bands. Stop inner band, take-profit 1.5R. Leakage: **PASS**. Long and short reported separately.

| Symbol | Timeframe | Side | Trades | Profit Factor | Annualized Sharpe | Win rate | Net PnL |
|--------|-----------|------|--------|---------------|-------------------|----------|---------|
| BTCUSDT | 15m | long | 9344 | 0.50 | −8.76 | 36.0% | −730.3 |
| BTCUSDT | 15m | short | 9323 | 0.49 | −8.37 | 35.0% | −774.8 |
| BTCUSDT | 1h | long | 2336 | 0.72 | −2.23 | 39.6% | −181.4 |
| BTCUSDT | 1h | short | 2246 | 0.67 | −2.60 | 37.7% | −215.4 |
| ETHUSDT | 15m | long | 9428 | 0.59 | — | 37.9% | −362.7 |
| ETHUSDT | 15m | short | 9374 | 0.63 | −6.23 | 38.2% | −325.0 |
| ETHUSDT | 1h | long | 2386 | 0.80 | −1.53 | 39.9% | −79.9 |
| ETHUSDT | 1h | short | 2249 | 0.81 | −1.38 | 39.6% | −73.6 |

**Action: FROZEN FAIL.** Do not search 0.5/3.0, add the 123 pattern, or change clocks because this screen lost. Inner-band stops are too tight versus taker costs.
