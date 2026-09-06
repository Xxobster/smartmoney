# Vortex Indicator — hypothesis-0

| Field | Value |
|-------|--------|
| **Maximum earned readiness** | `LIVE_STOP / RESEARCH_ONLY` |
| **Evidence class** | `EXPLORATORY_IN_SAMPLE` (full-history Hypothesis-0, not a 2027-style exam). Data: `RESEARCH_PROXY` (contaminated; engine stamp NOT GREEN) |
| **Principal blocker** | 1-hour legs Profit Factor (PF) 0.82–0.95. Best daily PF 1.02 (Bitcoin long n=60; Ethereum short n=54). Misses 1.20. |
| **Live-test candidate?** | **No** |

Public Vortex 14, VI+ / VI− cross, 2 × Average True Range 14 stop, 1.5R. Leakage: **PASS**.

| Symbol | Timeframe | Side | Trades | Profit Factor | Annualized Sharpe | Win rate | Net PnL |
|--------|-----------|------|--------|---------------|-------------------|----------|---------|
| BTCUSDT | 1h | long | 1633 | 0.84 | −1.09 | 42.7% | −132.9 |
| BTCUSDT | 1h | short | 1635 | 0.82 | −1.26 | 38.1% | −148.6 |
| BTCUSDT | 1d | long | 60 | 1.02 | 0.02 | 45.0% | +2.2 |
| BTCUSDT | 1d | short | 58 | 0.67 | −0.43 | 34.5% | −52.3 |
| ETHUSDT | 1h | long | 1579 | 0.89 | −0.71 | 43.6% | −53.0 |
| ETHUSDT | 1h | short | 1608 | 0.95 | −0.35 | 41.3% | −25.8 |
| ETHUSDT | 1d | long | 63 | 0.80 | −0.35 | 46.0% | −23.4 |
| ETHUSDT | 1d | short | 54 | 1.02 | 0.02 | 38.9% | +1.3 |

**Action: FROZEN FAIL.** Do not search length 9/21, add Average Directional Index, or add 15-minute because two daily legs sat near 1.02.
