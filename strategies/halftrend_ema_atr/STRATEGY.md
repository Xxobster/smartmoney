# Strategy: HalfTrend + Exponential Moving Average 60 + ATR exits (H0)

| Field | Value |
|-------|--------|
| **Source** | [`jjgeQUnZyz0`](https://www.youtube.com/watch?v=jjgeQUnZyz0) · TradeSmart **base recipe only** |
| **Readiness** | `LIVE_STOP / RESEARCH_ONLY` |
| **Evidence class** | `RESEARCH_PROXY` full-history Hypothesis-0 (H0) |

He showed a 90% win-rate claim, then “true” results near 28–35%, then **extra** filters (Exponential Moving Average 50/100/200, Chandemo, two-candle wait). Those extras are **not** used. Amplitude 6 / channel 2.4 in the extract JSON looks like an on-video search — **not** used.

## Frozen before our Profit Factor

- HalfTrend = Everget public defaults: amplitude **2**, channel deviation **2**, Average True Range (ATR) **100** ([TradingView](https://www.tradingview.com/script/U1SJ8ubc-HalfTrend/))
- Long: HalfTrend flips up (blue arrow) **and** close above Exponential Moving Average (EMA) **60**
- Short: HalfTrend flips down (red arrow) **and** close below EMA 60
- Stop 1.5 × ATR **14**; take-profit 3 × ATR 14 (his NFX ATR 1.5 / 3; ATR length 14 is the usual Wilder default, not a search)
- Clocks: **15-minute** and **1-hour** (video mentioned 5-minute too; 15-minute is the nearest crypto screen already used in this repo)
- Rising edge of the full condition set
- Long and short reported separately

Do **not** search amplitude 6, add 50/100/200, Chandemo, or 5-minute after viewing this H0.
