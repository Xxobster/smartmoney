# Current state — 2026-08-20

## Live vs backtest (full VPS94 chandelier, 2026-08-20)

Maximum earned readiness remains `LIVE_STOP / RESEARCH_ONLY`. Evidence class: `FORWARD_MICRO_LIVE_RECONCILE` + `RESEARCH_PROXY`.

Principal blocker: fills are not identical (Bybit market slip vs Binance next-open + 0.05% entry slip; backtester zero exit slip). **No material signal/stop/target/exit-reason mismatch.** 7 closed trades + 3 open longs match the research function. 1-minute path agrees with live stop vs take-profit (Bitcoin stop 12:04 live vs 12:08 Binance 1m). Do not raise size. Report: `artifacts/reports/tsm_chandelier/live_vs_bt_full_20260821.json`.

## Stage
SMC Gen1–Gen4 research family **abandoned for live**. Gen2 exact re-run **INVALIDATED** (same check as Gen4).

## Maximum earned readiness (SMC confluence / killzone line)
`LIVE_STOP / RESEARCH_ONLY`

## Gen2 exact re-run (today’s path)
Freeze: `2c65ce212a96ecb16e6519b55a8eaa39dacdf51cac5bc6a4e2d3797f1dd4af3a`

| | July report | Exact re-run 2026-08-12 |
|--|-------------|-------------------------|
| Net PnL | +111 | **−392** |
| PF | ~1.15 | **0.66** |
| Mean Sharpe | ~1.40 | **−4.13** |
| Folds | 5/5 green | **5/5 red** |
| Last 4m | — | **−32**, PF 0.77 |

Verdict: `invalidated: true`. Do not use Gen2 as a live or shadow candidate.

## SMC family decision
Abandon this Smart Money Concepts (SMC) confluence / killzone search line for live readiness. Negative / non-reproducible results are valid research outcomes. Any new work must be a **new preregistered generation** with a different economic hypothesis — not a least-bad retune of Gen2–4.

## What is live now (separate pack — not SMC)
Authorized micro-live on VPS 94 (`ln1` / 94.156.189.76), account **Xxobster6**:

- Pack: `tsm_chandelier_1h_btc_eth_sol_xxobster6_v1`
- Strategy: **tsm_chandelier** (ATR band + chandelier exit + EMA 50), **1h**, min size
- Symbols: **BTCUSDT, ETHUSDT, SOLUSDT** (SOL exploratory but user-authorized)
- Config: `deploy/tsm_chandelier/configs/live_btc_eth_sol_1h_xxobster6.json`
- SMC Gen2/3/4 is **not** deployed

## Authorization
SMC: `LIVE_STOP / RESEARCH_ONLY`.  
tsm_chandelier: user-explicit micro-live on Xxobster6 / VPS94 (min size) — separate from SMC research.

## Live vs backtest (closed ETH + BTC, 2026-08-13)

Maximum earned readiness remains `LIVE_STOP / RESEARCH_ONLY`. Evidence class: `FORWARD_MICRO_LIVE_RECONCILE` + `RESEARCH_PROXY`.

Both bots took the same short, same 1h bar, same stop/target, same min size, both exited on stop. End-to-end fills are **not identical**.

| | ETHUSDT | BTCUSDT |
|--|---------|---------|
| Live net | −0.20505348 (StopLoss market 1890.98 vs SL 1890.17) | −0.53846109 (StopLoss market 64243.3 vs SL 64240.6) |
| Backtest net | −0.20499 (stop at 1890.17, no exit slip) | −0.59588 (stop at 64240.6, no exit slip) |

Principal blocker: live StopLoss is Bybit market (taker + slip); canonical backtester fills the stop at the planned price with zero exit slip. Also: live market entry vs next-bar open+slip; live Bybit funding vs 0 in this re-sim. Do not raise size.
