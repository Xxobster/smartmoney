# Results — tsm_liquidity_sweep H0

## Verdict (lead)

| Item | Value |
|------|--------|
| **Maximum earned readiness** | `LIVE_STOP / RESEARCH_ONLY` |
| **Evidence class** | `RESEARCH_PROXY` (Binance OHLCV + Bybit cost model) |
| **Principal blocker** | No post-cost edge on full-history exploratory run; nested walk-forward / outer Out-Of-Sample (OOS) not earned. Engine conformance stamp was **NOT GREEN** at run time — numbers are diagnostic only. |

Negative / abandoned family outcome is a valid research result. Do **not** treat these full-history numbers as gate evidence.

## H0 baseline (2026-08-08)

Script: `strategies/tsm_liquidity_sweep/run_baseline.py`  
Artifact: `artifacts/reports/tsm_liquidity_sweep/baseline_h0.json`

| Symbol | Trades | Profit Factor (PF) | Ann. Sharpe | Max Drawdown (MDD) | Win Rate (WR) | Notes |
|--------|-------:|-------------------:|------------:|-------------------:|--------------:|-------|
| BTCUSDT | 5780 | 0.57 | −5.28 | (see report) | ~low | Over-trading; entry-bar exits high |
| ETHUSDT | 5794 | 0.64 | −4.25 | 2.31% | 30.9% | 26.8% entry-bar exits |

*(Post-causality-fix re-run. Still full-history exploratory only.)*

Costs charged (tradesim research defaults): Bybit non-VIP taker 0.055%, entry slip 0.05%, limit TP/SL at level without exit slip.

### Interpretation

1. Sweep+reclaim alone on 15m with tight ATR stop is **over-trading** (~37 trades/month) and dies to fees/slip.
2. High entry-bar exit rate ⇒ stop is inside ordinary bar noise (standard §9.6 warning).
3. Next research step is **not** blind TP/SL grid search. Either: redesign fold-length / confirmation (video’s multi-TF stop-hunt confirmation more strictly), or **abandon H0** after a small pre-registered redesign budget.

## Leakage

See [`LEAKAGE.md`](LEAKAGE.md). After fixing causal swing / Fair Value Gap (FVG) / Order Block (OB) attribution in `smc/`, audit is **PASS** (no hard fails; advisory `LEAKAGE_POTENTIAL` may remain).

## Engine fix note (2026-08-08)

Principal causality blockers found during this strategy’s audit (fixed in shared `smc/`):

1. Fractal swings used future bars / tagged pivot before confirmation  
2. FVG tagged on middle candle using candle-3 data  
3. Order Blocks wrote onto past opposing candles when impulse appeared later  

These invalidate prior SMC readiness hashes project-wide until re-run.
