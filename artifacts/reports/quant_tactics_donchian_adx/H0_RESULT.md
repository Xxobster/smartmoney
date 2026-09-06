# Donchian + Average Directional Index + Choppiness — hypothesis-0

| Field | Value |
|-------|--------|
| **Maximum earned readiness** | `LIVE_STOP / RESEARCH_ONLY` |
| **Evidence class** | `EXPLORATORY_IN_SAMPLE` (full-history Hypothesis-0, not a 2027-style exam). Data: `RESEARCH_PROXY` (contaminated; engine stamp NOT GREEN) |
| **Principal blocker** | Frozen Version 2.1 gates fail: only Ethereum short Profit Factor (PF) ≥ 1.20; annualized Sharpe well below 1.00 on every leg; Bitcoin both sides PF < 1 |
| **Live-test candidate?** | **No** |

Source: `CgYdfwrL1VQ` (Quant Tactics). Leakage: **PASS** (`LEAKAGE_POTENTIAL=0`).

Fair freeze (not a search): Donchian **20** prior-channel (shift-1), Exponential Moving Average (EMA) **50**, Average Directional Index (ADX) **14** > 20, Choppiness **14** < 40, stop **3 × Average True Range (ATR) 14** (trail omitted). Long and short reported separately.

| Symbol | Side | Trades | Trades/mo | PF | Sharpe (ann.) | Win rate | Net PnL |
|--------|------|--------|-----------|-----|---------------|----------|---------|
| ETHUSDT 1h | long | 354 | 4.4 | 1.05 | 0.12 | 38.7% | +7.0 |
| ETHUSDT 1h | short | 305 | 3.8 | 1.34 | 0.65 | 36.1% | +43.1 |
| BTCUSDT 1h | long | 351 | 4.4 | 0.92 | -0.20 | 39.3% | -21.0 |
| BTCUSDT 1h | short | 303 | 3.8 | 0.96 | -0.08 | 34.3% | -8.5 |

**FROZEN** — do not search Donchian length, Average Directional Index (ADX) threshold, Choppiness, or Average True Range (ATR) multiple on this full-history result. Ethereum short Profit Factor (PF) 1.34 is **not** a live or shadow candidate: no outer walk-forward, Sharpe 0.65 (Heteroskedasticity and Autocorrelation Consistent / HAC 0.69) below gates, and the other three legs fail Profit Factor (PF) 1.20.
