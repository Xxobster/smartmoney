# Strategy: Krown 5 Exponential Moving Average daily (H0)

| Field | Value |
|-------|--------|
| **Source** | [`C0wM-iKfwaI`](https://www.youtube.com/watch?v=C0wM-iKfwaI) · Krown |
| **Readiness** | `LIVE_STOP / RESEARCH_ONLY` |
| **Evidence class** | `RESEARCH_PROXY` full-history H0 |

## Stated rules

- Bitcoin daily: close above 5 Exponential Moving Average (EMA) → long; close below → exit
- No hard stop. Claimed Profit Factor ~2.72 since 2013, win rate ~31.6%
- On-video day-of-week clicks are **contaminated** (he looked at results while clicking). We do **not** copy Friday-skip as our search.

## Fair H0

- Long + **short_mirror** separate
- Stop at signal-bar 5 EMA (tradesim cannot trail a live EMA exit)
- Pre-registered improvement H0b: skip paper-cut crosses where |close−EMA| ≤ 0.25 × Average True Range 14 (his own paper-cut comment). Frozen 0.25 — not searched.

Results: `artifacts/reports/krown_ema5_daily/H0_RESULT.md`. Both H0 and H0b fail Frozen Version 2.1. **FROZEN.**
