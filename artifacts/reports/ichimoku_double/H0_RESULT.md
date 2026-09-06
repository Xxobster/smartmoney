# Double Ichimoku (daily bias + 4-hour Chikou) — hypothesis-0

| Field | Value |
|-------|--------|
| **Maximum earned readiness** | `LIVE_STOP / RESEARCH_ONLY` |
| **Evidence class** | `EXPLORATORY_IN_SAMPLE` (full-history Hypothesis-0, not a 2027-style exam). Data: `RESEARCH_PROXY` (engine stamp NOT GREEN) |
| **Principal blocker** | Frozen Version 2.1 gates fail: every 4-hour leg has Profit Factor (PF) below 1.20 and Sharpe well below 1.00; daily filter made the single-chart recipe worse |
| **Live-test candidate?** | **No** |

Source: `EpFv0L0sz9c` higher-timeframe-alignment tip + public multi-timeframe Ichimoku. Leakage: **PASS** (stop-price forward-correlation flag only, `LEAKAGE_POTENTIAL=1`).

Fair freeze (written before any Profit Factor, together with `ichimoku_chikou`): completed lagged daily close vs daily cloud and daily Tenkan vs Kijun; 4-hour Chikou fresh break + Tenkan/Kijun alignment; standard 9/26/52/26 on both frames; Kijun stop; 2R; max hold 48 four-hour bars.

Period: 2020-01-01 → 2026-04-19.

| Symbol | Side | Trades | PF | Sharpe (ann.) | HAC Sharpe | Win rate | Net PnL |
|--------|------|--------|-----|---------------|------------|----------|---------|
| BTCUSDT 4h | long | 102 | 0.45 | −1.01 | −1.07 | 28.4% | −44.4 |
| BTCUSDT 4h | short | 79 | 0.67 | −0.50 | −0.48 | 25.3% | −19.9 |
| ETHUSDT 4h | long | 80 | 0.87 | −0.17 | −0.18 | 32.5% | −4.6 |
| ETHUSDT 4h | short | 74 | 1.17 | 0.20 | 0.20 | 39.2% | +4.5 |

Ethereum short had 26% same-bar stop shakeouts (Kijun too close to price). Do **not** search weekly+daily, 1-hour execution, 9/26/52, or TradingView dual-cloud 10/30/60.

**FROZEN FAIL.** Not a live or shadow candidate.
