# Krown Bollinger Band Width Percentile squeeze + 200 SMA — hypothesis-0

| Field | Value |
|-------|--------|
| **Maximum earned readiness** | `LIVE_STOP / RESEARCH_ONLY` |
| **Evidence class** | `EXPLORATORY_IN_SAMPLE` (full-history Hypothesis-0, not a 2027-style exam). Data: `RESEARCH_PROXY` (engine stamp NOT GREEN) |
| **Principal blocker** | Frozen Version 2.1 gates fail: Profit Factor (PF) below 1.00 on every 4-hour leg; Sharpe negative |
| **Live-test candidate?** | **No** |

Source: `kcMnnQr1VFg` + `hNfjyrJEytI` (Krown). Leakage: **PASS** (`LEAKAGE_POTENTIAL=0`).

Fair freeze (written before our numbers): 4-hour only; Bollinger 7 ± 2 SMA; bandwidth percentile lookback 100; 5-period SMA of that percentile; squeeze-release = that SMA crosses up through 25; direction = close vs SMA 200; stop 2 × Average True Range (ATR) 14; take-profit 2R.

Period: 2020-01-01 → 2026-04-19.

| Symbol | Side | Trades | Trades/mo | PF | Sharpe (ann.) | HAC Sharpe | Win rate | Net PnL |
|--------|------|--------|-----------|-----|---------------|------------|----------|---------|
| BTCUSDT 4h | long | 171 | 2.26 | 0.83 | −0.39 | −0.40 | 34.5% | −30.3 |
| BTCUSDT 4h | short | 139 | 1.84 | 0.86 | −0.25 | −0.27 | 31.7% | −18.2 |
| ETHUSDT 4h | long | 157 | 2.08 | 1.00 | −0.01 | −0.01 | 37.6% | −0.4 |
| ETHUSDT 4h | short | 134 | 1.77 | 0.86 | −0.26 | −0.28 | 30.6% | −11.0 |

His “do not trade inside the squeeze” is already the entry. There is no second source-worded improvement to try after seeing these numbers. Do **not** search 25/85, lookback, or SMA 200.

**FROZEN.** Not a live or shadow candidate.
