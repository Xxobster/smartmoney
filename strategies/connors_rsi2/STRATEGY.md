# Strategy: Connors 2-period Relative Strength Index (H0)

| Field | Value |
|-------|--------|
| **Source** | Larry Connors published 2-period Relative Strength Index (RSI) mean-reversion (hunt video queued: `AMEO6VkZujY`). Same class as `cci_zero_line`: public internet default, not an on-video length search. |
| **Readiness** | `LIVE_STOP / RESEARCH_ONLY` |
| **Evidence class** | `RESEARCH_PROXY` full-history Hypothesis-0 (H0) |

Original was daily stocks, long-only. We do **not** copy any YouTube “best RSI settings after 200,000 trades” search (`tMxMQ1fBC6s`).

## Frozen before our Profit Factor

- RSI length **2**; buy when RSI crosses **below 5** (Connors original threshold, not 10)
- Take-profit: 5-period Simple Moving Average (SMA) (his mean-reversion exit)
- Disaster stop: **2 ×** Average True Range (ATR) **14** (written so the simulator has a stop; the book often used none)
- Clocks: **1-hour** and **daily** (daily = original; 1-hour = this repo’s crypto screen). Not 15-minute.
- Source side **long-only**; short_mirror reported separately (RSI crosses **above 95**, SMA-5 target, 2×ATR stop)

Do **not** search RSI 10, SMA length, 15-minute, or “200,000 trades” winners after viewing this H0.
