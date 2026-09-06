# Guppy Multiple Moving Average — hypothesis-0

| Field | Value |
|-------|--------|
| **Maximum earned readiness** | `LIVE_STOP / RESEARCH_ONLY` |
| **Evidence class** | `EXPLORATORY_IN_SAMPLE` (full-history Hypothesis-0, not a 2027-style exam). Data: `RESEARCH_PROXY` (contaminated; engine stamp NOT GREEN) |
| **Principal blocker** | 1-hour legs Profit Factor (PF) 0.85–0.95. Daily Ethereum short PF 1.78 has only **23 trades** (Sharpe 0.46) — sparse, not Frozen Version 2.1. |
| **Live-test candidate?** | **No** |

Public Guppy ribbon: short Exponential Moving Averages 3–15 fully above long 30–60. Stop 2 × Average True Range 14, 1.5R. Leakage: **PASS**.

| Symbol | Timeframe | Side | Trades | Profit Factor | Annualized Sharpe | Win rate | Net PnL |
|--------|-----------|------|--------|---------------|-------------------|----------|---------|
| BTCUSDT | 1h | long | 849 | 0.85 | −0.73 | 43.1% | −60.2 |
| BTCUSDT | 1h | short | 805 | 0.86 | −0.68 | 40.6% | −56.3 |
| BTCUSDT | 1d | long | 33 | 0.83 | −0.17 | 45.5% | −14.1 |
| BTCUSDT | 1d | short | 26 | 1.04 | 0.04 | 38.5% | +2.6 |
| ETHUSDT | 1h | long | 855 | 0.95 | −0.25 | 44.0% | −12.4 |
| ETHUSDT | 1h | short | 795 | 0.87 | −0.59 | 40.5% | −31.3 |
| ETHUSDT | 1d | long | 35 | 0.68 | −0.39 | 40.0% | −19.1 |
| ETHUSDT | 1d | short | 23 | 1.78 | 0.46 | 52.2% | +22.5 |

**Action: FROZEN FAIL.** Do not treat 23-trade PF 1.78 as a candidate. Do not add Relative Strength Index or 15-minute because that daily short printed above 1.20.
