# Strategy: The Secret Mindset — HTF EMA50 + VWAP outside candle

| Field | Value |
|-------|--------|
| **Source** | [BEST Chart Analysis System](https://www.youtube.com/watch?v=ZfkqKkI0YKI) (`ZfkqKkI0YKI`) · Batch 2 |
| **Readiness** | `LIVE_STOP / RESEARCH_ONLY` |
| **Evidence class** | `RESEARCH_PROXY` |

## H0

- Higher timeframe bias: **1h** close vs EMA(50) (up if close > EMA50)  
- Execution: **15m** (5m proxy avoided for cost; video uses 5m)  
- UTC-day Volume Weighted Average Price (VWAP) on execution TF  
- Bullish outside candle: engulfs prior bar range, close > open, bar trades through VWAP  
- Long only with 1h up bias; short with 1h down bias  
- Stop: outside-candle extreme; Take-Profit Reward:Risk **2.0**  

Symbols: `BTCUSDT`, `ETHUSDT`
