# Krown 5 Exponential Moving Average daily — hypothesis-0

| Field | Value |
|-------|--------|
| **Maximum earned readiness** | `LIVE_STOP / RESEARCH_ONLY` |
| **Evidence class** | `EXPLORATORY_IN_SAMPLE` (full-history Hypothesis-0, not a 2027-style exam). Data: `RESEARCH_PROXY` (contaminated vs his 2013 overlay claim; engine stamp NOT GREEN) |
| **Principal blocker** | Frozen Version 2.1 gates fail: annualized Sharpe 0.04–0.46 vs 1.00; 35–70% same-bar stop shakeouts; wallet return << buy-and-hold |
| **Live-test candidate?** | **No** |

Source: `C0wM-iKfwaI` (Krown). Leakage: **PASS** (`LEAKAGE_POTENTIAL=5` on price/Exponential Moving Average (EMA) forward-correlation, no hard fail).

His claim: overlay long when daily close > 5 EMA, exit when close < 5 EMA; Profit Factor (PF) ~2.72 since 2013, win rate ~31.6%, no hard stop. Fair H0 cannot trail a live EMA exit in tradesim, so the stop is the **signal-bar 5 EMA** plus max hold 40. That is incomplete versus the overlay and produces noisy same-bar exits.

On-video Friday-skip clicks are **contaminated**. We did **not** copy them.

Pre-registered improvement H0b (frozen from his “paper cut” comment, Average True Range (ATR) 14 × 0.25, not searched): skip tiny crosses.

Period: 2020-01-01 → 2026-04-19 (2300 days). Engine stamp NOT GREEN.

## H0 raw cross

| Symbol | Side | Trades | Trades/mo | PF | Sharpe (ann.) | HAC Sharpe | Win rate | Same-bar exit | Net PnL |
|--------|------|--------|-----------|-----|---------------|------------|----------|---------------|---------|
| BTCUSDT 1d | long | 218 | 2.88 | 1.33 | 0.38 | 0.35 | 6.4% | 63.8% | +45.7 |
| BTCUSDT 1d | short_mirror | 199 | 2.63 | 1.22 | 0.19 | 0.21 | 6.0% | 66.3% | +23.1 |
| ETHUSDT 1d | long | 237 | 3.14 | 1.03 | 0.04 | 0.04 | 5.5% | 66.7% | +2.7 |
| ETHUSDT 1d | short_mirror | 231 | 3.06 | 1.05 | 0.06 | 0.07 | 4.3% | 70.1% | +4.3 |

## H0b paper-cut (`\|close−EMA\| > 0.25 × ATR 14`)

| Symbol | Side | Trades | Trades/mo | PF | Sharpe (ann.) | HAC Sharpe | Win rate | Same-bar exit | Net PnL |
|--------|------|--------|-----------|-----|---------------|------------|----------|---------------|---------|
| BTCUSDT 1d | long | 101 | 1.34 | 1.47 | 0.46 | 0.42 | 10.9% | 41.6% | +48.8 |
| BTCUSDT 1d | short_mirror | 76 | 1.01 | 1.31 | 0.21 | 0.23 | 11.8% | 35.5% | +21.9 |
| ETHUSDT 1d | long | 91 | 1.20 | 1.43 | 0.41 | 0.42 | 14.3% | 40.7% | +24.0 |
| ETHUSDT 1d | short_mirror | 101 | 1.34 | 1.16 | 0.15 | 0.16 | 9.9% | 43.6% | +10.0 |

Paper-cut is slightly cleaner (fewer shakeouts, Bitcoin long PF 1.47 vs 1.33) and still fails Sharpe, Heteroskedasticity and Autocorrelation Consistent (HAC) Sharpe, and buy-and-hold comparison. Wallet return on the best leg is ~0.5% vs Bitcoin buy-and-hold ~925% over the same window.

**FROZEN** — do not search EMA length, ATR multiple, Friday-skip, or trail the live EMA after viewing these full-history numbers. Not a live or shadow candidate.
