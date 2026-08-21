# Results — tsm_rsi_momentum_fib H0

## Verdict

| Item | Value |
|------|--------|
| **Maximum earned readiness** | `LIVE_STOP / RESEARCH_ONLY` |
| **Evidence class** | `RESEARCH_PROXY` |
| **Principal blocker** | No post-cost edge on full-history exploratory run (PF &lt; 1) |
| **Leakage** | PASS (`LEAKAGE.md`) |

## Baseline (2026-08-08)

| Symbol | Trades | PF | Ann. Sharpe | Notes |
|--------|-------:|---:|------------:|-------|
| BTCUSDT | 3563 | 0.79 | −2.10 | Full-history only |
| ETHUSDT | 3723 | 0.89 | −1.05 | Entry-bar exits 7.5% (better than liquidity H0) |

Still **not** stitched outer-OOS evidence. Negative result is valid.
