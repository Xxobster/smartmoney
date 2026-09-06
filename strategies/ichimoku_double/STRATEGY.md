# Strategy: Double Ichimoku (daily bias + 4-hour Chikou entry) (H0)

| Field | Value |
|-------|--------|
| **Source** | Same Chikou recipe [`EpFv0L0sz9c`](https://www.youtube.com/watch?v=EpFv0L0sz9c) tip “higher time frame alignment”, plus the public multi-timeframe Ichimoku usage (higher-timeframe cloud/Tenkan-Kijun bias, lower-timeframe entry) |
| **Readiness** | `LIVE_STOP / RESEARCH_ONLY` |
| **Evidence class** | `RESEARCH_PROXY` full-history H0 |

## Frozen before any look at our numbers

This pack is **pre-registered together with** `ichimoku_chikou`, not an after-the-fact retune. His example was weekly Tenkan/Kijun plus daily Chikou; we freeze the same *idea* on crypto-tradeable bars: **completed lagged daily** bias + **4-hour** Chikou entry. We do **not** run weekly+daily or 1-hour execution, and we do **not** use TradingView dual-cloud 10/30/60.

- Higher timeframe (daily, lagged until the day is closed): close above the daily cloud **and** daily Tenkan above daily Kijun for longs (mirror for shorts)
- Execution (4-hour): same Chikou fresh break + Tenkan/Kijun alignment as `ichimoku_chikou`
- Standard 9/26/52/26 on **both** frames
- Stop = 4-hour signal-bar Kijun; take-profit **2R**; max hold **48** four-hour bars
- Long and short reported separately

Do **not** search timeframes, 9/26/52, or cloud-thickness filters after viewing results.
