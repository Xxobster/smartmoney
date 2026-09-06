# HalfTrend + Exponential Moving Average 60 + ATR 1.5/3 — hypothesis-0

| Field | Value |
|-------|--------|
| **Maximum earned readiness** | `LIVE_STOP / RESEARCH_ONLY` |
| **Evidence class** | `EXPLORATORY_IN_SAMPLE` (full-history Hypothesis-0, not a 2027-style exam). Data: `RESEARCH_PROXY` (contaminated; engine stamp NOT GREEN) |
| **Principal blocker** | All eight legs lose. Best Profit Factor (PF) 0.98 (Ethereum 1-hour long), annualized Sharpe −0.08. 15-minute is a fee grind (~40 trades/month). |
| **Live-test candidate?** | **No** |

Source: TradeSmart `jjgeQUnZyz0` **base recipe only**. Everget HalfTrend amplitude 2 / channel 2, Exponential Moving Average (EMA) 60, stop 1.5× Average True Range (ATR) 14, take-profit 3× ATR 14. Leakage: **PASS**. Long and short reported separately.

His 90% win-rate claim and the extra 50/100/200 EMA / Chandemo / two-candle filters were **not** used. Amplitude 6 was **not** used.

| Symbol | Timeframe | Side | Trades | Profit Factor | Annualized Sharpe | Win rate | Net PnL |
|--------|-----------|------|--------|---------------|-------------------|----------|---------|
| BTCUSDT | 15m | long | 3099 | 0.70 | −2.94 | 35.1% | −206.3 |
| BTCUSDT | 15m | short | 3044 | 0.63 | −3.86 | 32.8% | −271.1 |
| BTCUSDT | 1h | long | 750 | 0.88 | −0.54 | 39.3% | −36.7 |
| BTCUSDT | 1h | short | 730 | 0.92 | −0.36 | 35.6% | −26.4 |
| ETHUSDT | 15m | long | 3031 | 0.73 | −2.71 | 33.8% | −109.9 |
| ETHUSDT | 15m | short | 3076 | 0.79 | −1.96 | 34.5% | −90.1 |
| ETHUSDT | 1h | long | 729 | 0.98 | −0.08 | 38.1% | −3.3 |
| ETHUSDT | 1h | short | 738 | 0.96 | −0.15 | 35.1% | −6.9 |

**Action: FROZEN FAIL.** Do not search amplitude 6 / channel 2.4, add 50/100/200 Exponential Moving Averages, Chandemo, two-candle wait, or 5-minute because this screen lost.
