# Connors 2-period Relative Strength Index — hypothesis-0

| Field | Value |
|-------|--------|
| **Maximum earned readiness** | `LIVE_STOP / RESEARCH_ONLY` |
| **Evidence class** | `EXPLORATORY_IN_SAMPLE` (full-history Hypothesis-0, not a 2027-style exam). Data: `RESEARCH_PROXY` (contaminated; engine stamp NOT GREEN) |
| **Principal blocker** | All eight legs lose. Best Profit Factor (PF) 0.99 (Bitcoin daily long, 73 trades). 1-hour win rate ~59% but 5-period Simple Moving Average targets are too tight versus fees. |
| **Live-test candidate?** | **No** |

Public Connors default: Relative Strength Index 2 vs 5, take-profit at Simple Moving Average 5, disaster stop 2 × Average True Range 14. Leakage: **PASS** (potential flags, no hard-fail). Long + short_mirror reported separately.

| Symbol | Timeframe | Side | Trades | Profit Factor | Win rate | Net PnL |
|--------|-----------|------|--------|---------------|----------|---------|
| BTCUSDT | 1h | long | 1773 | 0.69 | 58.9% | −159.3 |
| BTCUSDT | 1h | short_mirror | 1834 | 0.64 | 57.6% | −177.7 |
| BTCUSDT | 1d | long | 73 | 0.99 | 64.4% | −1.2 |
| BTCUSDT | 1d | short_mirror | 92 | 0.92 | 55.4% | −8.1 |
| ETHUSDT | 1h | long | 1803 | 0.83 | 61.3% | −54.4 |
| ETHUSDT | 1h | short_mirror | 1844 | 0.73 | 58.6% | −77.6 |
| ETHUSDT | 1d | long | 58 | 0.76 | 60.3% | −11.3 |
| ETHUSDT | 1d | short_mirror | 82 | 0.58 | 40.2% | −28.7 |

**Action: FROZEN FAIL.** Do not search RSI threshold 10, Simple Moving Average length, or 15-minute, and do not copy “200,000 trades” RSI winners.
