# Keltner Channel breakout — hypothesis-0

| Field | Value |
|-------|--------|
| **Maximum earned readiness** | `LIVE_STOP / RESEARCH_ONLY` |
| **Evidence class** | `EXPLORATORY_IN_SAMPLE` (full-history Hypothesis-0, not a 2027-style exam). Data: `RESEARCH_PROXY` (contaminated; engine stamp NOT GREEN) |
| **Principal blocker** | No nested outer Out-Of-Sample; sparse daily trades; not deployment evidence |
| **Live-test candidate?** | **No** |

Source: `DhnwMO6bjQg`. Fair H0: Exponential Moving Average 20, Average True Range 20 × 2, next-open entry, stop at signal-bar middle. Long and `short_mirror` reported separately.

Leakage audit on features: **PASS**.

| Symbol | Timeframe | Side | Trades | Profit Factor | Annualized Sharpe | Win rate | Net PnL |
|--------|-----------|------|--------|---------------|-------------------|----------|---------|
| BTCUSDT | 4h | long | 122 | 1.09 | 0.15 | 25.4% | +16.5 |
| BTCUSDT | 4h | short_mirror | 97 | 1.01 | 0.01 | 29.9% | +1.3 |
| BTCUSDT | 1d | long | 23 | 3.44 | 1.00 | 60.9% | +97.1 |
| BTCUSDT | 1d | short_mirror | 17 | 2.26 | 0.37 | 52.9% | +34.8 |
| ETHUSDT | 4h | long | 111 | 1.50 | — | 31.5% | +45.8 |
| ETHUSDT | 4h | short_mirror | 91 | 1.39 | 0.32 | 31.9% | +26.5 |
| ETHUSDT | 1d | long | 26 | 2.91 | 0.78 | 57.7% | +55.1 |
| ETHUSDT | 1d | short_mirror | 18 | 1.24 | 0.14 | 44.4% | +8.2 |

**Action: FROZEN for parameter search.** Attractive daily Profit Factors are full-history / low trade-count and must not be optimized or promoted. A new preregistered nested walk-forward generation would be required before any shadow/live talk.
