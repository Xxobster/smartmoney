# Strategy: Hull Moving Average close-cross (H0)

| Field | Value |
|-------|--------|
| **Source** | [`zZQNhDGSUEI`](https://www.youtube.com/watch?v=zZQNhDGSUEI) · Roman — AlgoTrading Strategies |
| **Captions** | YouTube automatic English |
| **Readiness** | `LIVE_STOP / RESEARCH_ONLY` until gates say otherwise |
| **Evidence class** | `RESEARCH_PROXY` full-history Hypothesis-0 (H0) |

Creator heatmaps (Hull length ~140 on 4-hour, Sharpe grids) are **not** used. Spot-only / 0.1% fee claims are not copied; we use the canonical Bybit USDT perpetual cost model.

## Stated rules

- Market: Bitcoin / USDT (we also run Ethereum as a separate leg)
- Long when the candle **closes above** the Hull Moving Average (HMA)
- Exit when the candle **closes below** the HMA
- No separate stop-loss or take-profit in the transcript
- Timeframes discussed: daily, 4-hour, 2-hour (2-hour not in the research database)

## Fair H0 interpretation (frozen before our Profit Factor)

- HMA length **16** (Alan Hull 2005 textbook default — not the on-video heatmap winner)
- Entry: first close cross above HMA (long) / below HMA (`short_mirror`)
- Fill: engine next-open
- Exit approximation: causal **stop at the signal-bar HMA** plus a safety max-hold (no dynamic HMA trail in tradesim)
- Long and `short_mirror` are **separate** report rows — never pooled

## Action

**FROZEN FAIL** after H0 (`artifacts/reports/roman_hma_cross/H0_RESULT.md`). Do **not** search HMA length, slope-based KAMA-style rules, or Average True Range (ATR) stops after viewing this H0.
