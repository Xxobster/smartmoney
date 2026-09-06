# Commodity Channel Index zero-line — hypothesis-0

| Field | Value |
|-------|--------|
| **Maximum earned readiness** | `LIVE_STOP / RESEARCH_ONLY` |
| **Evidence class** | `EXPLORATORY_IN_SAMPLE` (full-history Hypothesis-0, not a 2027-style exam). Data: `RESEARCH_PROXY` (contaminated; engine stamp NOT GREEN) |
| **Principal blocker** | Profit Factor (PF) 0.80–0.87 and negative Sharpe on all four legs |
| **Live-test candidate?** | **No** |

Source: public internet default (CCI 14, zero-line cross). Leakage: **PASS**. Long and short tested separately.

| Symbol | Side | Trades | Trades/mo | PF | Sharpe (ann.) | Win rate | Net PnL |
|--------|------|--------|-----------|-----|---------------|----------|---------|
| BTCUSDT 1h | long | 1808 | 22.7 | 0.80 | −1.40 | 41.2% | −184.4 |
| BTCUSDT 1h | short | 1834 | 23.0 | 0.81 | −1.37 | 38.1% | −175.0 |
| ETHUSDT 1h | long | 1803 | 22.6 | 0.85 | −1.05 | 42.3% | −86.5 |
| ETHUSDT 1h | short | 1842 | 23.1 | 0.87 | −0.91 | 39.3% | −71.5 |

**FROZEN** — do not search Commodity Channel Index length or Average True Range multiple. Reverse sides lose about the same. High trades/month is not an edge. Not a live or shadow candidate.
