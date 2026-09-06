# Monday range sweep — hypothesis-0

| Field | Value |
|-------|--------|
| **Maximum earned readiness** | `LIVE_STOP / RESEARCH_ONLY` |
| **Evidence class** | `EXPLORATORY_IN_SAMPLE` (full-history Hypothesis-0, not a 2027-style exam). Data: `RESEARCH_PROXY` (contaminated; not a winner) |
| **Principal blocker** | Profit Factor below 1.00 on both legs; no nested outer Out-Of-Sample |
| **Action** | **FROZEN**. Do not optimize SuperTrend, session clock, 2R, or symbols on this result. |

Source: official YouTube captions for `BFdEPlNSaps`. Trigger 1 only (1-hour close outside the Monday range, then close back inside). Trigger 2 (Monday-open sweep) skipped. CoinQuant-app-only rules were not used.

Engine stamp is **NOT GREEN**. These numbers are not deployment evidence.

| Symbol | Trades | Profit Factor | Annualized Sharpe | Win rate | Net profit and loss |
|--------|--------|---------------|-------------------|----------|---------------------|
| Bitcoin USDT 1 hour | 114 (56 long / 58 short) | 0.38 | −1.26 | 9.6% | −31.13 |
| Ethereum USDT 1 hour | 119 (59 long / 60 short) | 0.85 | −0.25 | 22.7% | −4.43 |

A negative / gates-fail result is a valid research outcome.
