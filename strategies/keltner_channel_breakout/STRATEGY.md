# Strategy: Keltner Channel breakout (H0)

| Field | Value |
|-------|--------|
| **Source** | [`DhnwMO6bjQg`](https://www.youtube.com/watch?v=DhnwMO6bjQg) · Roman — AlgoTrading Strategies |
| **Captions** | YouTube automatic English |
| **Readiness** | `LIVE_STOP / RESEARCH_ONLY` until gates say otherwise |
| **Evidence class** | `RESEARCH_PROXY` full-history H0 |

Creator heatmaps (length 25 / multiplier 1, etc.) are **not** used. Spot-only / 0.1% fee claims are not copied; we use the canonical Bybit USDT perpetual cost model.

## Stated rules

- Market: Bitcoin / USDT (we also run Ethereum as a separate leg, reported alone)
- Long when close is above the upper Keltner band
- Exit when close is below the middle Exponential Moving Average (EMA)
- No separate stop-loss / take-profit in the transcript
- Timeframes discussed: daily, 4-hour, 2-hour (2-hour not in research database)

## Fair H0 interpretation

- EMA length **20**, Average True Range (ATR) length **20**, ATR multiplier **2**
- Entry: first close cross above upper (long) / below lower (`short_mirror`)
- Fill: engine next-open
- Exit approximation: causal **stop at middle band on the signal bar** (no dynamic mid trail in tradesim) + safety max_hold
- Long and `short_mirror` are **separate** report rows — never pooled

## Action

**FROZEN** after H0 (`artifacts/reports/keltner_channel_breakout/H0_RESULT.md`). Daily legs look strong on full history but are sparse and contaminated — **not** a live candidate. Do not search EMA length or ATR multiplier on that result.
