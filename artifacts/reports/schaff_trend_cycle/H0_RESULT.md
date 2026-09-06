# Schaff Trend Cycle — hypothesis-0

| Field | Value |
|-------|--------|
| **Maximum earned readiness** | `LIVE_STOP / RESEARCH_ONLY` |
| **Evidence class** | `EXPLORATORY_IN_SAMPLE` (full-history Hypothesis-0, not a 2027-style exam). Data: `RESEARCH_PROXY` (contaminated; engine stamp NOT GREEN) |
| **Principal blocker** | All liquid 1-hour legs lose (Profit Factor 0.79–0.90). Best daily Profit Factor 1.14 (Ethereum short, 59 trades, Sharpe 0.16) misses 1.20. |
| **Live-test candidate?** | **No** |

Public Schaff 23 / 50 / 10, cross 25 / 75, 2 × Average True Range 14 stop, 1.5R. Leakage: **PASS**.

| Symbol | Timeframe | Side | Trades | Profit Factor | Annualized Sharpe | Win rate | Net PnL |
|--------|-----------|------|--------|---------------|-------------------|----------|---------|
| BTCUSDT | 1h | long | 1523 | 0.90 | −0.65 | 43.9% | −79.1 |
| BTCUSDT | 1h | short | 1553 | 0.79 | −1.46 | 38.4% | −167.8 |
| BTCUSDT | 1d | long | 62 | 0.86 | −0.19 | 43.5% | −22.4 |
| BTCUSDT | 1d | short | 59 | 0.73 | −0.37 | 33.9% | −43.7 |
| ETHUSDT | 1h | long | 1518 | 0.87 | −0.80 | 43.9% | −61.7 |
| ETHUSDT | 1h | short | 1575 | 0.88 | −0.81 | 40.0% | −59.3 |
| ETHUSDT | 1d | long | 64 | 0.92 | −0.12 | 46.9% | −8.2 |
| ETHUSDT | 1d | short | 59 | 1.14 | 0.16 | 37.3% | +12.3 |

**Action: FROZEN FAIL.** Do not search 23/50/10 or 25/75, or add 15-minute, because Ethereum daily short was the least-bad leg.
