# Turkish Express + Hull 16 trend filter — hypothesis-0 mix

| Field | Value |
|-------|--------|
| **Maximum earned readiness** | `LIVE_STOP / RESEARCH_ONLY` |
| **Evidence class** | `EXPLORATORY_IN_SAMPLE` (full-history Hypothesis-0, not a 2027-style exam). Data: `RESEARCH_PROXY` (contaminated; engine stamp NOT GREEN) |
| **Principal blocker** | Mix was **worse** than EMA-200 Turkish Express: more trades, best PF 1.10 vs 1.14, Sharpe 0.30 vs 0.38 |
| **Live-test candidate?** | **No** |

Pre-registered mix of `J3be7tlxB6E` entries/exits with Hull Moving Average (HMA) **16** instead of Exponential Moving Average (EMA) 200. Leakage: **PASS**. Long and short reported separately.

| Symbol | Timeframe | Side | Trades | Profit Factor | Annualized Sharpe | Win rate | Net PnL |
|--------|-----------|------|--------|---------------|-------------------|----------|---------|
| BTCUSDT | 15m | long | 3203 | 0.82 | −1.43 | 31.7% | −174.0 |
| BTCUSDT | 15m | short | 2240 | 0.77 | −1.74 | 29.9% | −203.8 |
| BTCUSDT | 1h | long | 1080 | 0.97 | −0.13 | 37.3% | −14.5 |
| BTCUSDT | 1h | short | 719 | 0.87 | −0.51 | 33.0% | −59.6 |
| ETHUSDT | 15m | long | 3219 | 0.90 | −0.79 | 32.1% | −59.5 |
| ETHUSDT | 15m | short | 2207 | 0.95 | −0.30 | 31.8% | −26.6 |
| ETHUSDT | 1h | long | 1064 | 0.91 | −0.44 | 35.8% | −31.2 |
| ETHUSDT | 1h | short | 679 | 1.10 | 0.30 | 36.8% | +23.6 |

**Action: FROZEN FAIL.** Faster trend filter added churn, not edge. Do not search HMA length or drop Inverse Fisher on this sample.
