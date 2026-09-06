# Strategy: Turkish Express with Hull trend filter (H0 mix)

| Field | Value |
|-------|--------|
| **Sources** | Turkish Express [`J3be7tlxB6E`](https://www.youtube.com/watch?v=J3be7tlxB6E) **plus** Hull close-cross idea [`zZQNhDGSUEI`](https://www.youtube.com/watch?v=zZQNhDGSUEI) |
| **Readiness** | `LIVE_STOP / RESEARCH_ONLY` |
| **Evidence class** | `RESEARCH_PROXY` full-history Hypothesis-0 (H0) |

## Why this mix (written before any of our Profit Factors)

Hull Moving Average (HMA) 16 is a lower-lag trend line than Exponential Moving Average (EMA) 200. The economic hypothesis: keep the **same** MavilimW color + Inverse Fisher Transform ±0.5 + 10-bar swing stop + 3R exits, but replace EMA 200 with **HMA 16** so the bias filter reacts faster.

This pack is **pre-registered together with** `roman_hma_cross` and `turkish_express`. It is not an after-the-fact retune of a failed H0.

## Frozen rules

- Same as `turkish_express` except trend line = HMA **16** (Alan Hull default)
- Long: close > HMA 16; short: close < HMA 16
- Same 15-minute and 1-hour clocks, same holds, same Inverse Fisher levels
- Long and short reported separately

Do **not** search HMA length, add Average True Range (ATR) stops, or drop Inverse Fisher because this mix lost.

**FROZEN FAIL** after H0 (`artifacts/reports/turkish_express_hma/H0_RESULT.md`). The mix was worse than Exponential Moving Average (EMA) 200.
