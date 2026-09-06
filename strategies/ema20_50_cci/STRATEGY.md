# Strategy: 20/50 Exponential Moving Average + 200 EMA + CCI (H0)

| Field | Value |
|-------|--------|
| **Source** | [`RFMM8WkLXVI`](https://www.youtube.com/watch?v=RFMM8WkLXVI) · Crypto Trading |
| **Readiness** | `LIVE_STOP / RESEARCH_ONLY` |
| **Evidence class** | `RESEARCH_PROXY` full-history H0 |

## Stated rules (30-minute Bitcoin)

- Exponential Moving Average (EMA) 20 crosses EMA 50
- Both 20 and 50 above (long) or below (short) EMA 200
- Commodity Channel Index (CCI) above +100 (long) or below −100 (short)
- Stop = Average True Range (ATR) distance at the cross; take-profit **1.5R**

## Fair H0

- Mapped 30-minute → **1-hour** (project research timeframe with 1-minute touch)
- CCI 14, ATR 14 × 1.0 (lengths not stated; frozen, not searched)
- Personal session hours omitted
- Long and short reported separately
