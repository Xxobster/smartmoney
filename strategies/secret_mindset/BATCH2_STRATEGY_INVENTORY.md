# The Secret Mindset — Batch 2 strategy inventory

**Status:** Transcript pipeline **complete** (8/8 cleaned); packaging **7/8** (SMC overlap skipped)  
**Batch 1:** preserved — [`BATCH1_STRATEGY_INVENTORY.md`](BATCH1_STRATEGY_INVENTORY.md)  
**URLs:** `C:\projects\videoanalysis\data\secret_mindset\batch2_urls.txt`  
**Default readiness:** `LIVE_STOP / RESEARCH_ONLY`  
**Evidence class:** `RESEARCH_PROXY`  
**Engine stamp:** `NOT GREEN` (tradesim dirty) — numbers are not quotable deployment evidence

## Videos

| # | Video ID | Extracted name | Package | Disposition |
|---|----------|----------------|---------|-------------|
| 1 | `48gxeTt-Sdw` | HI-LO MA + Heikin Ashi + ADX | [`../tsm_hilo_ha_adx/`](../tsm_hilo_ha_adx/) | **FAIL** exploratory — 5m PF≈0.63–0.72 (~240 trades/mo); 15m PF≈0.77–0.84 (~101/mo) |
| 2 | `ZfkqKkI0YKI` | Trend + VWAP outside candle | [`../tsm_vwap_outside/`](../tsm_vwap_outside/) | **FAIL** — 15m PF≈0.56–0.67 (~33/mo) |
| 3 | `oF_NsJLMXEs` | VWAP + supply/demand | [`../tsm_vwap_sd/`](../tsm_vwap_sd/) | **FAIL** — 15m PF≈0.62–0.65; 1h PF≈0.89–0.93 |
| 4 | `Hq30qxOrScw` | Liquidity / mitigation (SMC) | *(skipped)* | Overlaps batch-1 `tsm_liquidity_sweep` family — do not duplicate until Gen redesign |
| 5 | `MTKAd1y1W30` | Breakout scoring | [`../tsm_breakout_score/`](../tsm_breakout_score/) | **ABANDON H0** — n≤3 after loosen; not tradeable |
| 6 | `owz1w37cVHs` | Impulse + volume PA | [`../tsm_impulse_volume/`](../tsm_impulse_volume/) | Exploratory 4h PF≈1.07–1.15; **nested OOS FAILED_GATES** (pooled PF 1.08 < 1.20) |
| 7 | `GkNhn-k05MY` | Failed breakout / trap | [`../tsm_failed_breakout/`](../tsm_failed_breakout/) | **FAIL** — 15m PF≈0.70–0.79; 1h PF≈0.87–0.95 |
| 8 | `H1x_XUEL2aY` | VWAP + RSI consensus | [`../tsm_vwap_rsi/`](../tsm_vwap_rsi/) | **FAIL** — 1h PF≈0.81–0.91 (~41/mo); 30m no_data |

## Nested outer Out-Of-Sample (OOS) — impulse 4h

- Generation: `tsm_impulse_volume_4h_h0_wf_20260810`  
- Config: `config/search_space_tsm_impulse_volume_4h.yaml`  
- Artifacts: `artifacts/reports/tsm_impulse_volume/4h_oos_*.json/md`  
- **Maximum earned readiness:** `LIVE_STOP / RESEARCH_ONLY_FAILED_GATES`  
- Pooled trades: **262** (~8.9/mo stitched) · pooled Profit Factor (PF) **1.08** · principal blocker: **pooled_pf** (need ≥1.20)  
- Do **not** open Take-Profit / Stop-Loss grids on this failed OOS.

## Policy

- Batch-1 packages and OOS evidence untouched.  
- Nested walk-forward only after preregistered fixed H0 with exploratory interest.  
- Negative / abandoned families are valid research outcomes.  
- Batch 3 not started unless explicitly requested.
