# Results — tsm_triple_ema_pullback H0

## Verdict

| Item | Value |
|------|--------|
| **Maximum earned readiness** | `LIVE_STOP / RESEARCH_ONLY` |
| **Evidence class** | `RESEARCH_PROXY` |
| **Leakage** | PASS |
| **Principal blocker** | No post-cost edge (all PF &lt; 1.0 on full-history exploratory) |

## Baseline (2026-08-08)

| Symbol | TF | Trades | PF | Ann. Sharpe | Status |
|--------|-----|------:|---:|------------:|--------|
| BTCUSDT | 15m | 408 | 0.644 | −1.12 | fail |
| ETHUSDT | 15m | 437 | 0.974 | −0.07 | fail (closest) |
| BTCUSDT | 1h | 97 | 0.716 | −0.46 | fail |
| ETHUSDT | 1h | 80 | 0.614 | −0.57 | fail |

Artifact: `artifacts/reports/tsm_triple_ema_pullback/baseline_h0.json`

ETHUSDT 15m is the least-bad Secret Mindset H0 so far (PF 0.97) but still not an edge after costs.
