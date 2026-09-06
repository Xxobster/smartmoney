# Strategy: Turkish Express — MavilimW + Inverse Fisher Transform (H0)

| Field | Value |
|-------|--------|
| **Source** | [`J3be7tlxB6E`](https://www.youtube.com/watch?v=J3be7tlxB6E) · Trader's Landing (Kivanc Ozbilgic indicators, **default** inputs) |
| **Captions / description** | Manual English + on-page system card |
| **Readiness** | `LIVE_STOP / RESEARCH_ONLY` |
| **Evidence class** | `RESEARCH_PROXY` full-history Hypothesis-0 (H0) |

Video tested **AMC** stock on **5-minute**. That is a different product. We do **not** copy his later “optimization tips” chapter.

## Stated rules (frozen)

- Trend: price above Exponential Moving Average (EMA) **200** for long; below for short
- MavilimW **default** (First 3, Second 5): blue = long bias, red = short bias
- Inverse Fisher Transform of Relative Strength Index (RSI): Kivanc default RSI **5**, smooth **9**
- Long: Inverse Fisher Transform **closes above −0.5**
- Short: Inverse Fisher Transform **closes below −0.5** (his written card; not the textbook +0.5 short line)
- Stop: previous swing low (long) / swing high (short)
- Take-profit: **3 times risk** (1:3)

## Fair H0 interpretation (frozen before our Profit Factor)

- Swing = prior **10-bar** extreme, excluding the signal bar
- Entry on the **rising edge** of the full condition set (not every bar in-regime)
- Clocks: **15-minute** and **1-hour** Bitcoin/Ethereum perpetuals (5-minute AMC is not this product; 15-minute is the nearest crypto clock already used in this repo’s The Secret Mindset screens). **Not** a search after numbers.
- Max-hold safety: 96 bars on 15-minute, 48 bars on 1-hour
- Long and short reported separately

## Action

**FROZEN FAIL** after H0 (`artifacts/reports/turkish_express/H0_RESULT.md`). Do **not** search EMA length, Inverse Fisher thresholds, swing lookback, Reward:Risk, or 5-minute crypto after viewing this H0.
