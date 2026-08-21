# Strategy: The Secret Mindset — VWAP + RSI consensus

| Field | Value |
|-------|--------|
| **Source** | [AI-Built RSI+VWAP Indicator](https://www.youtube.com/watch?v=H1x_XUEL2aY) (`H1x_XUEL2aY`) · Batch 2 |
| **Readiness** | `LIVE_STOP / RESEARCH_ONLY` |
| **Evidence class** | `RESEARCH_PROXY` |

## H0

- Session Volume Weighted Average Price (VWAP) reset each UTC day (crypto proxy)  
- Relative Strength Index (RSI)(14)  
- Long: close > VWAP and RSI crosses above 50  
- Short: close < VWAP and RSI crosses below 50  
- Stop: prior bar extreme; Take-Profit Reward:Risk **2.5**  
- Timeframes: **30m**, **1h** (video 30m / 4h — 1h used as liquid proxy)  

Symbols: `BTCUSDT`, `ETHUSDT`
