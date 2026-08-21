# Strategy: Trading Rush MACD cross below zero (H0)

| Field | Value |
|-------|--------|
| **Source** | [`B7jrlVeis6k`](https://www.youtube.com/watch?v=B7jrlVeis6k) · Trading Rush |
| **Captions** | Official YouTube automatic English captions (`youtube_auto`) |
| **Readiness** | `LIVE_STOP / RESEARCH_ONLY` |
| **Evidence class** | `RESEARCH_PROXY` |

Creator claims are **not** evidence. Original test: discretionary Gold versus US Dollar (`XAUUSD`), 30-minute entries. This package is a **mechanical transfer** onto Bitcoin / Ethereum Tether perpetuals.

## Stated rules (from captions)

- Indicator: default Moving Average Convergence Divergence (MACD: 12, 26, 9)
- Entry timeframe: **30 minutes**
- Long when the MACD line **crosses above** the signal line **and** that cross is **below the zero line**
- Extra filter: price above the **200-period moving average** on the entry timeframe
- Stop below the pullback / swing low (discretionary)
- Take-profit **1.5** times the stop distance
- Long only in that video (gold uptrend)
- Daily 9-period Exponential Moving Average and hand-drawn “red boxes” are discretionary market filters — **not coded**

## Our interpretation (not attributed to the creator)

- Stop = **low of the signal candle**
- Fill = **next bar open**
- Test **15 minute** and **1 hour**
- Symbols: `BTCUSDT`, `ETHUSDT`
- Max hold 96 bars (15 minute) / 48 bars (1 hour)

## Availability

`FREE_STANDARD` — Open-High-Low-Close-Volume only.

## Independent H0 result (frozen fail)

Maximum earned readiness: `LIVE_STOP / RESEARCH_ONLY`. Evidence class: `RESEARCH_PROXY`.

Leakage audit: **PASS**. Full-history baseline: **all four legs FAIL**.

| Symbol | Timeframe | Trades | Profit Factor | Annualized Sharpe | Win rate |
|--------|-----------|--------|---------------|-------------------|----------|
| BTCUSDT | 1h | 429 | 0.49 | −1.71 | 34.0% |
| ETHUSDT | 1h | 453 | 0.70 | −1.02 | 37.5% |
| BTCUSDT | 15m | 1920 | 0.40 | −4.87 | 30.4% |
| ETHUSDT | 15m | 1872 | 0.44 | −4.44 | 32.6% |

Entry-bar exits 38–42%. Do **not** optimize MACD lengths, zero-line rule, or reward multiple on this result.

## Do not optimize

This H0 is frozen-failed. Search is stopped.
