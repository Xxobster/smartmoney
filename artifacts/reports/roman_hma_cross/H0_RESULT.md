# Hull Moving Average close-cross — hypothesis-0

| Field | Value |
|-------|--------|
| **Maximum earned readiness** | `LIVE_STOP / RESEARCH_ONLY` |
| **Evidence class** | `EXPLORATORY_IN_SAMPLE` (full-history Hypothesis-0, not a 2027-style exam). Data: `RESEARCH_PROXY` (contaminated; engine stamp NOT GREEN) |
| **Principal blocker** | Profit Factor (PF) ≤ 1.09; win rate ~5–9%; **55–61%** same-bar stop shakeouts (stop at signal-bar Hull is inside bar noise) |
| **Live-test candidate?** | **No** |

Source: `zZQNhDGSUEI`. Fair H0: Hull Moving Average (HMA) length **16**, next-open entry, stop at signal-bar HMA. Long and `short_mirror` reported separately. Leakage: **PASS**.

| Symbol | Timeframe | Side | Trades | Profit Factor | Annualized Sharpe | Win rate | Net PnL |
|--------|-----------|------|--------|---------------|-------------------|----------|---------|
| BTCUSDT | 4h | long | 820 | 1.00 | −0.01 | 5.4% | −0.9 |
| BTCUSDT | 4h | short_mirror | 879 | 0.70 | −0.65 | 4.7% | −89.8 |
| BTCUSDT | 1d | long | 181 | 0.93 | −0.08 | 6.6% | −11.0 |
| BTCUSDT | 1d | short_mirror | 174 | 1.06 | 0.06 | 6.9% | +7.9 |
| ETHUSDT | 4h | long | 793 | 1.05 | 0.10 | 6.3% | +9.0 |
| ETHUSDT | 4h | short_mirror | 899 | 1.09 | 0.16 | 5.2% | +15.2 |
| ETHUSDT | 1d | long | 179 | 1.09 | 0.11 | 8.9% | +7.9 |
| ETHUSDT | 1d | short_mirror | 202 | 0.79 | −0.27 | 5.0% | −19.2 |

**Action: FROZEN FAIL.** Do not search HMA length, slope rules, or Average True Range (ATR) stops on this sample. Same-channel Keltner daily numbers are a different pack and stay frozen separately.
