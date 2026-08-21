# Strategy: The Secret Mindset — Chandelier / ATR band breakout (H0)

| Field | Value |
|-------|--------|
| **Source** | [`HzkU6cbcI1o`](https://www.youtube.com/watch?v=HzkU6cbcI1o) · channel continuation |
| **Readiness** | `LIVE_STOP / SHADOW_READY` (historical; not live authorization) |
| **Evidence class** | `RESEARCH_PROXY` (Binance OHLCV + Last-as-Mark; Bybit costs) |
| **Gate BCD** | `artifacts/reports/tsm_chandelier/1h_gate_bcd_sitrep.md` |
| **Freeze** | `artifacts/reports/tsm_chandelier/1h_SHADOW_FREEZE.json` |
| **Shadow runbook** | [`SHADOW_RUNBOOK.md`](SHADOW_RUNBOOK.md) |

## H0

- ATR(14) bands around close: ± 2.5×ATR  
- Long: close breaks above upper band; short: below lower  
- Trend filter: close > EMA(50) longs / < shorts  
- Stop: Chandelier = highest(22) − 3×ATR (long) / lowest(22) + 3×ATR (short)  
- No fixed Take-Profit — exit on opposite Chandelier touch or max hold  
- Timeframes: **15m**, **1h**

Symbols: `BTCUSDT`, `ETHUSDT`
