# SuperTrend + Exponential Moving Average 200 — hypothesis-0

| Field | Value |
|-------|--------|
| **Maximum earned readiness** | `LIVE_STOP / RESEARCH_ONLY` |
| **Evidence class** | `EXPLORATORY_IN_SAMPLE` (full-history Hypothesis-0, not a 2027-style exam). Data: `RESEARCH_PROXY` (contaminated; engine stamp NOT GREEN) |
| **Principal blocker** | No nested outer Out-Of-Sample. Best Sharpe 0.98 misses Frozen Version 2.1 (≥1.00). Heteroskedasticity and Autocorrelation Consistent (HAC) Sharpe 0.92. His 2,529% was an eight-coin Freqtrade book, not this min-size single-coin screen. |
| **Live-test candidate?** | **No** |

Source: `53yqW60SDPk`. Fair H0: SuperTrend 8×4, Exponential Moving Average (EMA) 200, 1.5× Average True Range (ATR) 8 stop, 4-hour only. **Not** a chandelier retune. Leakage: **PASS**. Long and short reported separately.

| Symbol | Timeframe | Side | Trades | Profit Factor | Annualized Sharpe | Win rate | Net PnL |
|--------|-----------|------|--------|---------------|-------------------|----------|---------|
| BTCUSDT | 4h | long | 108 | 1.37 | 0.45 | 20.4% | +38.7 |
| BTCUSDT | 4h | short | 101 | 1.04 | 0.05 | 21.8% | +4.8 |
| ETHUSDT | 4h | long | 103 | 1.95 | 0.98 | 26.2% | +57.8 |
| ETHUSDT | 4h | short | 95 | 0.98 | −0.02 | 23.2% | −1.2 |

**Action: FROZEN.** Attractive Ethereum long full-history Profit Factor (PF) 1.95 does **not** earn shadow or live. Do not search SuperTrend length, add 1-hour, or copy the eight-coin book because Sharpe was close to 1.00.
