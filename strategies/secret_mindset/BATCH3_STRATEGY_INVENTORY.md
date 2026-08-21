# The Secret Mindset — Batch 3 strategy inventory

**Status:** Transcript pipeline **complete** (8/8) · packaging **done**  
**Prior batches:** [`BATCH1_STRATEGY_INVENTORY.md`](BATCH1_STRATEGY_INVENTORY.md) · [`BATCH2_STRATEGY_INVENTORY.md`](BATCH2_STRATEGY_INVENTORY.md)  
**URLs:** `C:\projects\videoanalysis\data\secret_mindset\batch3_urls.txt`  
**Default readiness:** `LIVE_STOP / RESEARCH_ONLY`  
**Evidence class:** `RESEARCH_PROXY`  
**Engine stamp:** `NOT GREEN`

## Videos

| # | Video ID | Extracted theme | Package | Disposition |
|---|----------|-----------------|---------|-------------|
| 1 | `rThEVFW75Ew` | Flag + 21/55 EMA | [`../tsm_flag_ema2155/`](../tsm_flag_ema2155/) | **FAIL** 1h PF≈0.83–0.94 · 4h≈0.74–0.75 |
| 2 | `_8q3ZJ5afFA` | Monthly pivot + Bollinger | [`../tsm_pivot_bb/`](../tsm_pivot_bb/) | Mixed — ETH 1d PF≈1.33 (n=87) / BTC fail; no OOS |
| 3 | `VxQqfNkLiuc` | Pattern-failure trap | *(skipped)* | Weak extract; overlaps `tsm_failed_breakout` |
| 4 | `UQR4rM9L6Fg` | Bullish engulfing at demand | [`../tsm_engulf_demand/`](../tsm_engulf_demand/) | **Best TSM nested OOS:** PF **1.56**, 91 trades, 5/5 +folds — `FAILED_GATES` (Sharpe 0.45) |
| 5 | `7XhVy9z5SbM` | EMA 50/100/150 scalp | *(skipped)* | Same family as `tsm_triple_ema_pullback` |
| 6 | `yPbUn3Wuh98` | EMA 20/200 trend | [`../tsm_ema20_200/`](../tsm_ema20_200/) | **FAIL** 1d PF≈0.90–0.98; 4h≈0.93–1.07 |
| 7 | `En2ZIfAyhBg` | 21/55 ribbon pullback | [`../tsm_ema2155_ribbon/`](../tsm_ema2155_ribbon/) | **FAIL** 1h PF≈0.84–0.89; 4h≈0.94–0.96 |
| 8 | `4rn1vw3kGuU` | ADX/DMI + OBV | [`../tsm_adx_dmi_obv/`](../tsm_adx_dmi_obv/) | Sparse/mixed — ETH 4h PF≈1.53 (n=37); BTC fail; 1d n≤6 |

## Nested outer Out-Of-Sample (OOS) — engulf demand 4h

- Generation: `tsm_engulf_demand_4h_h0_wf_20260810`  
- Artifacts: `artifacts/reports/tsm_engulf_demand/4h_oos_*.json/md`  
- **Maximum earned readiness:** `LIVE_STOP / RESEARCH_ONLY_FAILED_GATES`  
- Pooled PF **1.56** · Sharpe **0.45** · HAC **0.49** · positive fold frac **100%**  
- Principal blocker: **sharpe** (need ≥1.00 annualized)  
- Do **not** open Take-Profit / Stop-Loss grids on this failed OOS.

## Policy

- Batches 1–2 untouched.  
- Negative / skipped families are valid outcomes.  
- Batch 4 not started unless requested.
