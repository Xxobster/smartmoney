# Ichimoku Tenkan/Kijun + Chikou span breakout — hypothesis-0

| Field | Value |
|-------|--------|
| **Maximum earned readiness** | `LIVE_STOP / RESEARCH_ONLY` |
| **Evidence class** | `EXPLORATORY_IN_SAMPLE` (full-history Hypothesis-0, not a 2027-style exam). Data: `RESEARCH_PROXY` (engine stamp NOT GREEN) |
| **Principal blocker** | Frozen Version 2.1 gates fail: only Ethereum short Profit Factor (PF) ≥ 1.20, and that leg’s annualized Sharpe is 0.38 |
| **Live-test candidate?** | **No** |

Source: `EpFv0L0sz9c`. Leakage: **PASS** (`LEAKAGE_POTENTIAL=0`).

Fair freeze (written before our numbers): 4-hour only; Tenkan 9, Kijun 26, Senkou B 52, displacement 26; Tenkan/Kijun is alignment not entry; Chikou fresh break of the candle 26 bars ago; stop at signal-bar Kijun; take-profit 2R.

Period: 2020-01-01 → 2026-04-19.

| Symbol | Side | Trades | PF | Sharpe (ann.) | HAC Sharpe | Win rate | Net PnL |
|--------|------|--------|-----|---------------|------------|----------|---------|
| BTCUSDT 4h | long | 236 | 0.75 | −0.64 | −0.68 | 34.3% | −47.7 |
| BTCUSDT 4h | short | 255 | 0.90 | −0.24 | −0.24 | 30.6% | −17.5 |
| ETHUSDT 4h | long | 247 | 0.78 | −0.57 | −0.55 | 34.8% | −26.9 |
| ETHUSDT 4h | short | 248 | 1.21 | 0.38 | 0.39 | 33.9% | +18.3 |

The pre-registered higher-timeframe filter is the separate pack `ichimoku_double` (frozen before these numbers). Do **not** search 9/26/52, displacement, or 1-hour / daily execution on this sample.

**FROZEN FAIL** except the one Ethereum short PF print, which still fails Sharpe. Not a live or shadow candidate.
