# Strategy: The Secret Mindset — RSI + ADX + EMA Scalp

| Field | Value |
|-------|--------|
| **Source** | [Scalping … EMA RSI ADX](https://www.youtube.com/watch?v=vBM0imYSzxI) (`vBM0imYSzxI`) |
| **Readiness** | `LIVE_STOP / RESEARCH_ONLY` |
| **Evidence class** | `RESEARCH_PROXY` |

## H0 (executable)

- Timeframe: **5m** (also report **15m** sensitivity)
- EMA50 trend filter  
- RSI(3): long when RSI ≤ 20; short when RSI ≥ 80  
- ADX(5) > 30  
- Long only if close > EMA50; short if close < EMA50  
- Entry on signal bar close (research next-open fill via tradesim)  
- Stop: signal-bar extreme; Take-Profit Reward:Risk **1.0**  
- Session filter: London/NY hours UTC 07–21 (optional ON in H0)

Symbols: `BTCUSDT`, `ETHUSDT`
