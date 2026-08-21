# Strategy: The Secret Mindset — Pressure Zone (shadow overlap)

| Field | Value |
|-------|--------|
| **Source** | [AGGRESSIVE Price Action Strategy](https://www.youtube.com/watch?v=0dNxenQznZY) (`0dNxenQznZY`) |
| **Readiness** | `LIVE_STOP / RESEARCH_ONLY` |
| **Evidence class** | `RESEARCH_PROXY` |

## H0 (executable)

- Timeframes: **1h** and **1d**
- **Bullish zone:** three consecutive bars with overlapping lower shadows  
  - zone bottom = lowest low of the three  
  - zone top = lowest close of the three bodies  
- **Bearish zone:** three consecutive bars with overlapping upper shadows  
  - zone top = highest high of the three  
  - zone bottom = highest close of the three bodies  
- Interval overlap: `max(lows) < min(body_lows)` (bull) / `max(body_highs) < min(highs)` (bear); each bar must have a non-zero shadow on that side  
- **Long entry:** third bar of the zone if bullish and closes above zone top; else next bar if it overlaps the zone, closes above zone top, and has not closed below zone bottom  
- **Short entry:** mirror  
- **Stop:** just beyond the formation extreme (zone bottom for longs / zone top for shorts) — matches the video’s “low/high of that week” when the three bars are the weekly formation  
- **Take-Profit:** Reward:Risk **2.0** (video leaves Take-Profit discretionary; frozen research assumption)  
- **Filter:** long only if close > Exponential Moving Average (EMA) 50; short only if close < EMA50  

Symbols: `BTCUSDT`, `ETHUSDT`
