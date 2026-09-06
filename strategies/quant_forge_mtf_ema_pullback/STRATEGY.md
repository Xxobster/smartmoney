# Strategy: Quant Forge multi-timeframe EMA pullback (H0)

| Field | Value |
|-------|--------|
| **Source** | [`DkTJiMHZLFE`](https://www.youtube.com/watch?v=DkTJiMHZLFE) · Quant Forge |
| **Readiness** | `LIVE_STOP / RESEARCH_ONLY` |
| **Evidence class** | `RESEARCH_PROXY` full-history H0 |

## Stated rules

- Bitcoin only; 4-hour 200 Exponential Moving Average (EMA) trend filter with upward/downward slope
- 1-hour pullback to 20 EMA with volume confirmation candle
- Stop: 1.2 × Average True Range (ATR) 14
- Exit: 50% at 1R; trail remainder on 1-hour 20 EMA

## Fair H0 interpretation

- 4-hour filter from resampled 1-hour bars (completed-bar lag via `lag_htf_to_ltf`)
- Slope default: EMA200 vs 5 completed 4-hour bars prior
- Pullback: touch 1-hour 20 EMA, close on correct side, volume > prior bar
- Full position take-profit at 1R (partial + EMA trail omitted)
- Event / compressed-ATR filters omitted
- Long and short reported **separately** — never pooled
