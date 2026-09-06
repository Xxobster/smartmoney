# Strategy: SuperTrend + Exponential Moving Average 200 (H0)

| Field | Value |
|-------|--------|
| **Source** | [`53yqW60SDPk`](https://www.youtube.com/watch?v=53yqW60SDPk) · Quant Tactics |
| **Captions** | YouTube automatic English (length **8**, multiplier **4.0**, 4-hour, Average True Range stop **1.5**) |
| **Readiness** | `LIVE_STOP / RESEARCH_ONLY` |
| **Evidence class** | `RESEARCH_PROXY` full-history Hypothesis-0 (H0) |

This is **not** a chandelier retune. Chandelier is a different pack (Average True Range band break + chandelier stop). This recipe is SuperTrend flip + Exponential Moving Average (EMA) 200 filter.

He locked **one** 4-hour clock (said he did not shop timeframes). Paid Freqtrade file / eight-coin portfolio / max 8 open trades are **not** copied. We run Bitcoin and Ethereum **separately**.

## Stated rules

- SuperTrend length 8, multiplier 4.0
- Long: price above SuperTrend **and** above EMA 200
- Short: price below SuperTrend **and** below EMA 200
- Exit: SuperTrend flips against the position
- Stop: 1.5 × Average True Range (ATR)

## Fair H0 interpretation (frozen before our Profit Factor)

- ATR period for the 1.5 stop = SuperTrend length **8** (same series; not a search)
- Entry on the **rising edge** of the full condition set
- Stop at `close − 1.5×ATR` (long) / `close + 1.5×ATR` (short). SuperTrend flip is not a separate trailing order in tradesim; max-hold **96** four-hour bars is a safety cap
- Clock: **4-hour only**
- Long and short reported separately

Do **not** search SuperTrend length/multiplier, add 1-hour, or copy the eight-coin Freqtrade book after viewing this H0.

**FROZEN** after H0 (`artifacts/reports/quant_tactics_st_ema200/H0_RESULT.md`). Ethereum 4-hour long Profit Factor 1.95 / Sharpe 0.98 is full-history only — not live.
