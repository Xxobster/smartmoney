# Strategy: CoinQuant Average Directional Index regime (H0)

| Field | Value |
|-------|--------|
| **Source** | [`pD1gDYnLRu0`](https://www.youtube.com/watch?v=pD1gDYnLRu0) · CoinQuant builder video |
| **Captions** | Official YouTube automatic English captions (`youtube_auto`) |
| **Readiness** | `LIVE_STOP / RESEARCH_ONLY` |
| **Evidence class** | `RESEARCH_PROXY` |

Creator claims (every year profitable, Profit Factor 1.67) are **not** evidence. CoinQuant is `PAID_OPTIONAL`; the rules below are from captions, not the app.

## Stated rules

- Market: Bitcoin Tether (`BTCUSDT`), 1 hour
- Average Directional Index (ADX) 14: **> 20** = trend mode; **< 16** = range mode; **16–20** = no trade
- Trend long: 1h close **above** 4-hour linear regression length **50**; 1h linear-regression slope length **100** **> 0**; close **crosses above** lower Bollinger Band; Relative Strength Index (RSI) 14 **> 20**
- Range long: drop regression filters; close crosses above lower Bollinger Band and RSI 14 **< 35**
- Shorts: mirrored
- Trend exits stated: take-profit **5.5%**, stop **1.5%**
- Range exit stated as mid-band, but creator said the platform **ignored** that and used 5.5% / 1.5%

## Our interpretation

- Bollinger default **20, 2** (not stated)
- Use **5.5% / 1.5%** on all trades (what they actually simulated)
- 4-hour regression uses only **completed** 4-hour bars
- Fill = next bar open
- Also transfer to `ETHUSDT` 1 hour

## Independent H0 result (does not pass gates)

Maximum earned readiness: `LIVE_STOP / RESEARCH_ONLY`. Evidence class: `RESEARCH_PROXY` (full history, not nested outer Out-Of-Sample).

Leakage audit: **PASS**.

| Symbol | Timeframe | Trades | Profit Factor | Annualized Sharpe | Win rate |
|--------|-----------|--------|---------------|-------------------|----------|
| BTCUSDT | 1h | 308 | 1.33 | 0.71 | 32.5% |
| ETHUSDT | 1h | 348 | 1.04 | 0.10 | 27.6% |

Bitcoin Tether Profit Factor above 1.20 on **inspected full history** is **not** `SHADOW_READY`. Frozen V2.1 still needs ≥5 outer folds, pooled Profit Factor, annualized Sharpe ≥ 1.00, and no selection on this sample. Ethereum fails Profit Factor 1.20.

Do **not** optimize Average Directional Index thresholds, Bollinger length, or take-profit / stop-loss on this result. Do **not** start walk-forward on the same history after viewing these numbers.

## Do not optimize

Search is stopped on this family.
