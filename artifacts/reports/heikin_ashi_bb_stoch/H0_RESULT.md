# Heikin Ashi × Bollinger × Stochastic RSI — hypothesis-0

| Field | Value |
|-------|--------|
| **Maximum earned readiness** | `LIVE_STOP / RESEARCH_ONLY` |
| **Evidence class** | `EXPLORATORY_IN_SAMPLE` (full-history Hypothesis-0, not a 2027-style exam). Data: `RESEARCH_PROXY` (contaminated; engine stamp NOT GREEN) |
| **Principal blocker** | Profit factor (PF) below 1 on all four legs |
| **Live-test candidate?** | **No** |

Source: `qP2XkQcr2eU`. Leakage: **PASS** (LEAKAGE_POTENTIAL=1 on stop name).

| Symbol | Side | Trades | Trades/mo | PF | Sharpe (ann.) | Win rate | Net PnL |
|--------|------|--------|-----------|-----|---------------|----------|---------|
| BTCUSDT 1h | long | 673 | 8.4 | 0.69 | -1.31 | 49.9% | -60.3 |
| BTCUSDT 1h | short | 590 | 7.4 | 0.86 | -0.47 | 52.0% | -20.3 |
| ETHUSDT 1h | long | 674 | 8.5 | 0.80 | -0.79 | 51.2% | -23.8 |
| ETHUSDT 1h | short | 559 | 7.0 | 0.96 | -0.14 | 51.5% | -3.7 |

**FROZEN** — do not search Bollinger length, Stochastic thresholds, or Heikin Ashi exit on this full-history result. Not a live or shadow candidate.
