# Quant Forge MTF EMA pullback — hypothesis-0

| Field | Value |
|-------|--------|
| **Maximum earned readiness** | `LIVE_STOP / RESEARCH_ONLY` |
| **Evidence class** | `EXPLORATORY_IN_SAMPLE` (full-history Hypothesis-0, not a 2027-style exam). Data: `RESEARCH_PROXY` (contaminated; engine stamp NOT GREEN) |
| **Principal blocker** | Profit factor (PF) below 1 on both sides; matches video’s weak PF ~0.39 |
| **Live-test candidate?** | **No** |

Source: `DkTJiMHZLFE`. Leakage: **PASS**.

| Symbol | Side | Trades | Trades/mo | PF | Sharpe (ann.) | Win rate | Net PnL |
|--------|------|--------|-----------|-----|---------------|----------|---------|
| BTCUSDT 1h | long | 1334 | 16.7 | 0.70 | -2.02 | 51.4% | -110.4 |
| BTCUSDT 1h | short | 1269 | 15.9 | 0.68 | -2.22 | 49.0% | -116.5 |

**FROZEN** — do not optimize EMA lengths, ATR stop, or filters on this full-history result. Not a live or shadow candidate.
