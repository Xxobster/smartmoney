# Parabolic Stop and Reverse + EMA 200 + RSI — hypothesis-0

| Field | Value |
|-------|--------|
| **Maximum earned readiness** | `LIVE_STOP / RESEARCH_ONLY` |
| **Evidence class** | `EXPLORATORY_IN_SAMPLE` (full-history Hypothesis-0, not a 2027-style exam). Data: `RESEARCH_PROXY` (contaminated; engine stamp NOT GREEN) |
| **Principal blocker** | Profit Factor (PF) below 1.20 on every 4-hour leg; annualized Sharpe ≤ 0.35 |
| **Live-test candidate?** | **No** |

Source: `RdHzNY0K2ws`. Leakage: **PASS**. Long and short tested separately (reverse included).

| Symbol | Side | Trades | Trades/mo | PF | Sharpe (ann.) | Win rate | Net PnL |
|--------|------|--------|-----------|-----|---------------|----------|---------|
| BTCUSDT 4h | long | 203 | 2.69 | 1.17 | 0.35 | 46.3% | +39.5 |
| BTCUSDT 4h | short | 163 | 2.16 | 1.16 | 0.29 | 48.5% | +33.1 |
| ETHUSDT 4h | long | 213 | 2.82 | 0.93 | −0.17 | 44.6% | −12.1 |
| ETHUSDT 4h | short | 179 | 2.37 | 1.13 | 0.24 | 42.5% | +17.0 |

**FROZEN** — do not search Parabolic Stop and Reverse step/max, Exponential Moving Average length, or Relative Strength Index threshold. Reverse sides are not better enough to pass gates. Not a live or shadow candidate.
