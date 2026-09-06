# LazyBear Squeeze Momentum — hypothesis-0

| Field | Value |
|-------|--------|
| **Maximum earned readiness** | `LIVE_STOP / RESEARCH_ONLY` |
| **Evidence class** | `EXPLORATORY_IN_SAMPLE` (full-history Hypothesis-0, not a 2027-style exam). Data: `RESEARCH_PROXY` (contaminated; engine stamp NOT GREEN) |
| **Principal blocker** | 1-hour legs Profit Factor (PF) 0.78–0.98. Daily Ethereum short PF 1.23 has only 47 trades (Sharpe 0.23). Not Frozen Version 2.1. |
| **Live-test candidate?** | **No** |

Source: `GXqXYW12x_I`. LazyBear defaults, histogram sign, Average True Range (ATR) 14 × 1.5 stop, 1R. Leakage: **PASS**. Long and short reported separately. Not a Bollinger Band Width Percentile retune.

| Symbol | Timeframe | Side | Trades | Profit Factor | Annualized Sharpe | Win rate | Net PnL |
|--------|-----------|------|--------|---------------|-------------------|----------|---------|
| BTCUSDT | 1h | long | 1412 | 0.78 | — | 53.0% | −102.0 |
| BTCUSDT | 1h | short | 1400 | 0.84 | — | 51.2% | −68.2 |
| BTCUSDT | 1d | long | 57 | 1.16 | — | 57.9% | +13.2 |
| BTCUSDT | 1d | short | 56 | 0.83 | — | 46.4% | −17.4 |
| ETHUSDT | 1h | long | 1400 | 0.80 | — | 52.6% | −57.2 |
| ETHUSDT | 1h | short | 1402 | 0.98 | — | 53.4% | −6.3 |
| ETHUSDT | 1d | long | 48 | 0.65 | — | 50.0% | −20.3 |
| ETHUSDT | 1d | short | 47 | 1.23 | 0.23 | 46.8% | +10.9 |

**Action: FROZEN FAIL** on the 1-hour sample. Daily PF 1.23 is sparse — do not treat it as a candidate. Do not add 30-minute because 1-hour lost, search length 20, or copy Krown squeeze settings.
