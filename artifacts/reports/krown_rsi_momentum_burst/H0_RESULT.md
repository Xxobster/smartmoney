# Krown hourly Relative Strength Index momentum burst — hypothesis-0

| Field | Value |
|-------|--------|
| **Maximum earned readiness** | `LIVE_STOP / RESEARCH_ONLY` |
| **Evidence class** | `EXPLORATORY_IN_SAMPLE` (full-history Hypothesis-0, not a 2027-style exam). Data: `RESEARCH_PROXY` (engine stamp NOT GREEN) |
| **Principal blocker** | Frozen Version 2.1 gates fail: best annualized Sharpe 0.53 (Ethereum long) vs 1.00; Bitcoin long Profit Factor (PF) 1.14 < 1.20; both short_mirror legs lose |
| **Live-test candidate?** | **No** |

Source: `hTcz81O2w-o` (Krown). Leakage: **PASS** (`LEAKAGE_POTENTIAL=0`).

Fair freeze (public four-rule recipe, **not** the 576-variant search): 1-hour Relative Strength Index (RSI) 14 fresh cross through 70; close above 1-hour 200 Simple Moving Average (SMA); completed lagged 4-hour RSI > 50; completed lagged daily RSI > 50; exit at 24 hours (`max_hold_bars=24`); no stop. Long and short_mirror reported separately. Higher-timeframe RSI uses only completed candles (stricter than a live overlay of the in-progress 4-hour).

Period: 2020-01-01 → 2026-08-25 (~2428 days).

| Symbol | Side | Trades | Trades/mo | PF | Sharpe (ann.) | HAC Sharpe | Win rate | Net PnL |
|--------|------|--------|-----------|-----|---------------|------------|----------|---------|
| BTCUSDT 1h | long | 301 | 3.77 | 1.14 | 0.31 | 0.34 | 50.2% | +20.2 |
| BTCUSDT 1h | short_mirror | 242 | 3.03 | 0.85 | −0.34 | −0.38 | 41.7% | −25.9 |
| ETHUSDT 1h | long | 314 | 3.94 | 1.26 | 0.53 | 0.58 | 49.0% | +22.0 |
| ETHUSDT 1h | short_mirror | 249 | 3.12 | 0.66 | −0.84 | −0.81 | 41.8% | −40.9 |

Ethereum long clears Profit Factor (PF) 1.20 but Sharpe 0.53 (Heteroskedasticity and Autocorrelation Consistent / HAC 0.58) is well below 1.00 / 0.75. Wallet return ~0.2% vs Ethereum buy-and-hold ~1823% over the same window. Short_mirror is the inverse (cross down 30, below SMA, higher-timeframe RSI < 50) and **loses**. His on-video “smart exits” already failed in *his* 576 search; we do **not** retry those after seeing our numbers.

**FROZEN** — do not search RSI length, 70/50 levels, SMA length, hold hours, or 576-search winners on this full-history result. Not a live or shadow candidate.
