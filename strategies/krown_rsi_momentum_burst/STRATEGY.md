# Strategy: Krown hourly Relative Strength Index momentum burst (H0)

| Field | Value |
|-------|--------|
| **Source** | [`hTcz81O2w-o`](https://www.youtube.com/watch?v=hTcz81O2w-o) · Krown |
| **Readiness** | `LIVE_STOP / RESEARCH_ONLY` |
| **Evidence class** | `RESEARCH_PROXY` full-history H0 |

## Stated rules (public four-block recipe)

- Bitcoin 1-hour: Relative Strength Index (RSI) 14 **fresh** cross above 70
- Close above 1-hour 200 Simple Moving Average (SMA)
- 4-hour RSI 14 above 50
- Daily RSI 14 above 50
- Exit exactly 24 hours later; no stop, no target, one position at a time

He then searched **576** exits/filters on camera. We **do not** copy that search or its winners.

## Fair H0

- Long + **short_mirror** separate (cross down 30, below SMA, higher-timeframe RSI below 50)
- Higher-timeframe RSI uses only **completed, lagged** 4-hour and daily candles (stricter than a live overlay of the in-progress 4-hour)
- Time exit via `max_hold_bars=24`; no stop in tradesim

Results: `artifacts/reports/krown_rsi_momentum_burst/H0_RESULT.md`. **FROZEN.** Do not copy the 576-variant search.
