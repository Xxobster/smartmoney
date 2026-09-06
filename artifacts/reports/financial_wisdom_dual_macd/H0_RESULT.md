# Weekly + daily Moving Average Convergence Divergence — hypothesis-0

| Field | Value |
|-------|--------|
| **Maximum earned readiness** | `LIVE_STOP / RESEARCH_ONLY` |
| **Evidence class** | `EXPLORATORY_IN_SAMPLE` (full-history Hypothesis-0, not a 2027-style exam). Data: `RESEARCH_PROXY` (contaminated; engine stamp NOT GREEN) |
| **Principal blocker** | Sparse trades (<1/month); wick stop shaken out on >25% of entries; Sharpe well below 1.00 |
| **Live-test candidate?** | **No** |

Source: `Gzl43lj2tS4` (long-only). Leakage: **PASS** (LEAKAGE_POTENTIAL=5). **short_mirror** run separately.

| Symbol | Side | Trades | Trades/mo | PF | Sharpe (ann.) | Win rate | Net PnL |
|--------|------|--------|-----------|-----|---------------|----------|---------|
| BTCUSDT 1d | long | 32 | 0.42 | 1.69 | 0.38 | 12.5% | +33.6 |
| BTCUSDT 1d | short_mirror | 57 | 0.75 | 0.92 | −0.06 | 15.8% | −8.2 |
| ETHUSDT 1d | long | 36 | 0.48 | 0.96 | −0.02 | 13.9% | −1.6 |
| ETHUSDT 1d | short_mirror | 60 | 0.79 | 1.83 | 0.50 | 18.3% | +41.8 |

Bitcoin long Profit Factor (PF) 1.69 and Ethereum short_mirror PF 1.83 are **not** live-ready: 32–60 trades, Win Rate ~13–18%, 28–39% entry-bar exits, Sharpe 0.38 / 0.50. **FROZEN** — do not search MACD 12/26/9. Reverse helped Ethereum vs the original long, still fails Frozen Version 2.1.
