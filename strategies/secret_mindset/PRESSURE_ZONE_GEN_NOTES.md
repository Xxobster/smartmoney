# Pressure zone — next-generation notes (not yet preregistered)

**Current max readiness:** `LIVE_STOP / RESEARCH_ONLY_FAILED_GATES`  
**Evidence:** nested 1d OOS pooled PF 1.24 / Sharpe 0.30 / positive eligible folds 60%  
**Do not** open a Take-Profit / Stop-Loss grid on the failed generation.

## What the OOS already showed

- Sample size OK (137 pooled trades, 5 eligible folds).  
- Profit Factor cleared the 1.20 floor; risk-adjusted return and fold stability did not.  
- Edge is uneven across folds (diagnostic only — not for selection).

## Allowed redesign directions (new YAML generation required)

1. **Economic rule change** — e.g. require break-and-retest of the zone, or higher-timeframe Exponential Moving Average alignment beyond the current filter.  
2. **Session / symbol scope freeze** — only if justified economically *before* viewing new OOS (not because one fold looked better).  
3. **Fold redesign** only if a new rule makes the strategy sparser; do not lower gate thresholds.

## Forbidden

- Ranking exits or filters on outer OOS.  
- Claiming `SHADOW_READY` without Deflated Sharpe Ratio, bootstrap, and stress modules.
