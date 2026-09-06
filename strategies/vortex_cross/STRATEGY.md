# Strategy: Vortex Indicator (H0)

| Field | Value |
|-------|--------|
| **Source** | Botes / Siepman public 14-period Vortex (internet default, same class as `cci_zero_line`). |
| **Readiness** | `LIVE_STOP / RESEARCH_ONLY` |
| **Evidence class** | `RESEARCH_PROXY` full-history Hypothesis-0 (H0) |

## Frozen before our Profit Factor

- Vortex length **14**
- Long: VI+ crosses **above** VI−. Short: VI− crosses **above** VI+.
- Stop **2 ×** Average True Range (ATR) **14**; take-profit **1.5R** (written)
- Clocks: **1-hour** and **daily**
- Long and short reported separately. **No** Average Directional Index filter (that would be an extra search).

Do **not** search length 9/21, add Average Directional Index, or add 15-minute after viewing this H0.
