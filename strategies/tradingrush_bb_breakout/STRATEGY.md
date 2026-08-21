# Strategy: Trading Rush Bollinger Band close-break (H0)

| Field | Value |
|-------|--------|
| **Source** | [`8_QWC2KzRUA`](https://www.youtube.com/watch?v=8_QWC2KzRUA) · Trading Rush |
| **Captions** | Official YouTube automatic English captions (`youtube_auto`) |
| **Readiness** | `LIVE_STOP / RESEARCH_ONLY` |
| **Evidence class** | `RESEARCH_PROXY` |

Creator claims are **not** evidence. The original test was discretionary Gold versus US Dollar (`XAUUSD`) on 30-minute bars. This package is a **mechanical transfer** onto Bitcoin / Ethereum Tether perpetuals.

## Stated rules (from captions)

- Indicator: default Bollinger Bands (period **20**, 2 standard deviations; creator said settings were not changed)
- Timeframe for entry: **30 minutes**
- Long when a candle **closes above** the upper band
- Entry at that **closing price** (stated)
- Stop below the pullback / swing low of the trend (discretionary)
- Take-profit **1.5** times the stop distance
- Extra filter: price also above the **200-period moving average** on the entry timeframe
- Long only in that video (gold uptrend)
- Percent B is only a visual helper for the same band break

## Our interpretation (not attributed to the creator)

- Do **not** code the discretionary “extremely good market” red boxes or the daily 9-period moving-average regime sketch
- Stop = **low of the signal candle** (mechanical stand-in for “below the pullback”)
- Fill = **next bar open** (close-based signal is known only after the close)
- Test **15 minute** (closest listed research timeframe to 30 minute) and **1 hour**
- Symbols: `BTCUSDT`, `ETHUSDT` — not gold
- Max hold 96 bars so the engine cannot leave orphans

## Availability

`FREE_STANDARD` — Open-High-Low-Close-Volume only.

## Independent H0 result (frozen fail)

Maximum earned readiness: `LIVE_STOP / RESEARCH_ONLY`. Evidence class: `RESEARCH_PROXY` (not gold, not 30-minute, not Out-Of-Sample).

Leakage audit: **PASS**. Full-history baseline (Bybit-style costs, next-open fill): **all four legs FAIL**.

| Symbol | Timeframe | Trades | Profit Factor | Annualized Sharpe | Win rate |
|--------|-----------|--------|---------------|-------------------|----------|
| BTCUSDT | 1h | 1014 | 0.86 | −0.69 | 42.6% |
| ETHUSDT | 1h | 1018 | 0.96 | −0.18 | 43.2% |
| BTCUSDT | 15m | 3843 | 0.63 | −3.89 | 39.0% |
| ETHUSDT | 15m | 3842 | 0.72 | −2.97 | 40.0% |

Fees exceed net edge on every leg. Do **not** optimize Bollinger length, band width, reward multiple, hold, or symbols on this result.

## Do not optimize

This H0 is frozen-failed. Search is stopped.
