# Current state — 2026-09-04

## Installed rules pack

Hunting agents use `C:\projects\BASE CURSOR\TRADING_BOT_CURSOR_RULES_V2.zip`. After copy, hashes live in `docs/project_memory/INSTALLED_STANDARD_HASHES.md`. Practice vs exam: `docs/project_memory/IN_SAMPLE_VS_OOS.md`. **No research-generation search is open** (`RESEARCH_GENERATION_FREEZE.md`).

## Video analysis — HARVESTED 2026-09-04

Scout keep-alive restarted. User-queue still has dozens of pending YouTube IDs. Seed-scout auto-resume can sit in front of the user-URL caption worker.

Canonical test index: `docs/project_memory/H0_TEST_REGISTRY.md`.

## Hypothesis-0 packs — 4 Sep 2026 (QQE, Squeeze, Connors RSI-2)

Maximum earned readiness: `LIVE_STOP / RESEARCH_ONLY`. Evidence class: `EXPLORATORY_IN_SAMPLE`. Data: `RESEARCH_PROXY`. **No live-test candidate.**

- `qqe_mod_zero` (`N3A8g083dWY`): QQE MOD zero-cross + Exponential Moving Average 200 + 1.5R swing. Best Profit Factor (PF) 0.95. **FROZEN FAIL**. Report: `artifacts/reports/qqe_mod_zero/H0_RESULT.md`.
- `lazybear_squeeze_mom` (`GXqXYW12x_I`): LazyBear histogram sign, 1-hour + daily. 1-hour PF 0.78–0.98; daily Ethereum short PF 1.23 (n=47, Sharpe 0.23). **FROZEN FAIL**. Report: `artifacts/reports/lazybear_squeeze_mom/H0_RESULT.md`.
- `connors_rsi2`: Relative Strength Index 2 vs 5, Simple Moving Average 5 target. Best PF 0.99. **FROZEN FAIL**. Report: `artifacts/reports/connors_rsi2/H0_RESULT.md`.
- `elder_impulse`: Exponential Moving Average 13 + Moving Average Convergence Divergence histogram. 1-hour loses; daily Ethereum short PF 1.23 (n=82, Sharpe 0.31). **FROZEN FAIL**. Report: `artifacts/reports/elder_impulse/H0_RESULT.md`.
- `kst_cross`: Know Sure Thing vs signal 9. Best PF 1.17 (Bitcoin daily long, 52 trades). **FROZEN FAIL**. Report: `artifacts/reports/kst_cross/H0_RESULT.md`.
- `guppy_mma`: Guppy ribbon 3–15 vs 30–60. 1-hour loses; daily Ethereum short PF 1.78 (n=23). **FROZEN FAIL**. Report: `artifacts/reports/guppy_mma/H0_RESULT.md`.
- `schaff_trend_cycle`: Schaff 23/50/10 cross 25/75. Best PF 1.14 (Ethereum daily short, 59 trades). **FROZEN FAIL**. Report: `artifacts/reports/schaff_trend_cycle/H0_RESULT.md`.
- `vortex_cross`: Vortex 14 VI+ / VI− cross. Best PF 1.02. **FROZEN FAIL**. Report: `artifacts/reports/vortex_cross/H0_RESULT.md`.

## Hypothesis-0 pack — 4 Sep 2026 (HalfTrend + EMA 60)

Maximum earned readiness: `LIVE_STOP / RESEARCH_ONLY`. Evidence class: `EXPLORATORY_IN_SAMPLE`. Data: `RESEARCH_PROXY`. **No live-test candidate.**

- `halftrend_ema_atr` (`jjgeQUnZyz0`): Everget HalfTrend amplitude 2 / channel 2 + Exponential Moving Average 60 + 1.5/3 Average True Range 14, 15-minute and 1-hour. Best Profit Factor (PF) 0.98 (Ethereum 1-hour long), Sharpe −0.08. All eight legs lose. **FROZEN FAIL** — do not search amplitude 6, extra moving averages, Chandemo, or 5-minute. Report: `artifacts/reports/halftrend_ema_atr/H0_RESULT.md`.

## Hypothesis-0 packs — 1 Sep 2026 (SuperTrend+EMA200, Double Bollinger)

Maximum earned readiness: `LIVE_STOP / RESEARCH_ONLY`. Evidence class: `EXPLORATORY_IN_SAMPLE`. Data: `RESEARCH_PROXY`. **No live-test candidate.**

- `quant_tactics_st_ema200` (`53yqW60SDPk`): SuperTrend 8×4 + Exponential Moving Average 200, 4-hour. Ethereum long Profit Factor (PF) 1.95, Sharpe 0.98, n=103. **FROZEN** — not nested Out-Of-Sample, not a chandelier retune, do not add 1-hour because Sharpe was close to 1.00. Report: `artifacts/reports/quant_tactics_st_ema200/H0_RESULT.md`.
- `double_bb_range_break` (`0cn9mAnOoX0`): inner 0.5-sigma range then prior-bar break. Best PF 0.81. **FROZEN FAIL**. Report: `artifacts/reports/double_bb_range_break/H0_RESULT.md`.

## Hypothesis-0 packs — 1 Sep 2026 (Hull MA, Turkish Express, mix)

Maximum earned readiness: `LIVE_STOP / RESEARCH_ONLY`. Evidence class: `EXPLORATORY_IN_SAMPLE` (full-history Hypothesis-0 screen, not a 2027-style exam). Data: `RESEARCH_PROXY` (engine stamp NOT GREEN). **No live-test candidate.**

- `roman_hma_cross` (`zZQNhDGSUEI`): Hull Moving Average 16 close-cross, 4-hour + daily. Best Profit Factor (PF) 1.09, Sharpe 0.16; **55%+** same-bar stops. **FROZEN FAIL**. Report: `artifacts/reports/roman_hma_cross/H0_RESULT.md`.
- `turkish_express` (`J3be7tlxB6E`): Exponential Moving Average 200 + MavilimW + Inverse Fisher −0.5 + 3R swing. Best PF 1.14 (Ethereum 1-hour short), Sharpe 0.38. **FROZEN FAIL**. Report: `artifacts/reports/turkish_express/H0_RESULT.md`.
- `turkish_express_hma` (pre-registered mix): same entries with Hull 16 instead of Exponential Moving Average 200. Best PF 1.10 — **worse** than the EMA-200 pack. **FROZEN FAIL**. Report: `artifacts/reports/turkish_express_hma/H0_RESULT.md`.


## EXEC-021 / 1-minute fill-clock fleet (1 Sep 2026)

Maximum earned readiness: `LIVE_STOP / RESEARCH_ONLY`. Evidence class: `EXPLORATORY_IN_SAMPLE`. Data: `RESEARCH_PROXY`. **No new live-test candidate.**

Old Hypothesis-0 runs used Bitcoin/Ethereum 1-minute bars only from 2026-08-01, so 2020–2026 take-profit/stop used the decision-bar fallback (stop-first). That is illegal under engine identifier EXEC-021. 1-minute history was backfilled from Binance Vision (2020-01-01 onward; Solana from listing). Fleet: `research/run_exec021_fleet.py` → `artifacts/reports/exec021_fleet/FLEET_RESULT.md`.

- **Live (this project only):** `tsm_chandelier` on VPS94 / Xxobster6, **market** entry, **5% wallet-equity cash risk** (round down to qty step, **floor at exchange min**), 1-hour Bitcoin/Ethereum/Solana. Honest live-match column is `taker_market` for **entry**. Take-profit / stop are bot-placed maker limits (`TP_SL_MAKER.md`). 15-minute legs lose. Do not raise size beyond this 5% rule. `exec021_limit` is a Post-Only **entry** diagnostic, not how the bot enters today.
- **Not live:** 41 other packs with `signals.py`. Zero rows with ≥50 trades, Profit Factor ≥ 1.20, **and** Sharpe ≥ 1.00. Do not search parameters on this file.

## Hypothesis-0 packs — 1 Sep 2026 (Ichimoku + double Ichimoku)

Maximum earned readiness: `LIVE_STOP / RESEARCH_ONLY`. Evidence class: `EXPLORATORY_IN_SAMPLE` (full-history Hypothesis-0 screen, not a 2027-style exam). Data: `RESEARCH_PROXY` (engine stamp NOT GREEN). **No live-test candidate.**

- `ichimoku_chikou` (`EpFv0L0sz9c`): 4-hour Tenkan/Kijun alignment + Chikou span break of the past candle; Kijun stop, 2R. Best Profit Factor (PF) 1.21 (Ethereum short), Sharpe 0.38. Other legs PF 0.75–0.90. **FROZEN**. Report: `artifacts/reports/ichimoku_chikou/H0_RESULT.md`.
- `ichimoku_double` (same video’s higher-timeframe tip, frozen before numbers): lagged daily cloud/Tenkan-Kijun bias + same 4-hour entry. Best PF 1.17; Bitcoin longs PF 0.45. Daily filter made the recipe worse. **FROZEN**. Report: `artifacts/reports/ichimoku_double/H0_RESULT.md`.


## Hypothesis-0 packs — 31 Aug 2026 (BBWP squeeze, 20/50 EMA+CCI)

Maximum earned readiness: `LIVE_STOP / RESEARCH_ONLY`. Evidence class: `EXPLORATORY_IN_SAMPLE` (full-history Hypothesis-0 screen, not a 2027-style exam). Data: `RESEARCH_PROXY`. **No live-test candidate.**

- `krown_bbwp_squeeze` (`kcMnnQr1VFg`): 4-hour Bollinger Band Width Percentile squeeze-release + 200 Simple Moving Average. Best PF ~1.00 (Ethereum long, still negative PnL). **FROZEN**. Report: `artifacts/reports/krown_bbwp_squeeze/H0_RESULT.md`.
- `ema20_50_cci` (`RFMM8WkLXVI`): 1-hour EMA 20/50 cross + EMA 200 + Commodity Channel Index ±100. Best PF 0.92. **FROZEN**. Report: `artifacts/reports/ema20_50_cci/H0_RESULT.md`.

## Hypothesis-0 packs — 30 Aug 2026 (Krown)

Maximum earned readiness: `LIVE_STOP / RESEARCH_ONLY`. Evidence class: `EXPLORATORY_IN_SAMPLE` (full-history Hypothesis-0 screen, not a 2027-style exam). Data: `RESEARCH_PROXY` (engine stamp NOT GREEN). **No live-test candidate.** Channel notes: `docs/project_memory/KROWN_NOTES.md`.

- `krown_ema5_daily` (`C0wM-iKfwaI`): daily 5 Exponential Moving Average (EMA) overlay. Best H0 Profit Factor (PF) 1.33 (Bitcoin long); paper-cut H0b 1.47. Sharpe ≤ 0.46; 35–70% same-bar stop shakeouts. **FROZEN** — do not search EMA length or Friday-skip. Report: `artifacts/reports/krown_ema5_daily/H0_RESULT.md`.
- `krown_rsi_momentum_burst` (`hTcz81O2w-o`): 1-hour Relative Strength Index (RSI) ignition + 200 Simple Moving Average (SMA) + lagged 4-hour/daily RSI > 50; 24-hour time exit. Best PF 1.26 (Ethereum long), Sharpe 0.53; shorts lose. **FROZEN** — do not copy the 576-variant search. Report: `artifacts/reports/krown_rsi_momentum_burst/H0_RESULT.md`.

## Hypothesis-0 packs — 30 Aug 2026 (Parabolic SAR, Dual MACD, CCI)

Maximum earned readiness: `LIVE_STOP / RESEARCH_ONLY`. Evidence class: `EXPLORATORY_IN_SAMPLE` (full-history Hypothesis-0 screen, not a 2027-style exam). Data: `RESEARCH_PROXY`. **No live-test candidate.** Reverse sides were run on every pack. Do not search parameters on these inspected results.

- `aly_psar_ema_rsi` (`RdHzNY0K2ws`): 4h both sides; best PF 1.17; Sharpe ≤ 0.35. FROZEN.
- `financial_wisdom_dual_macd` (`Gzl43lj2tS4`): daily long + short_mirror; BTC long PF 1.69 / ETH short_mirror PF 1.83 but sparse, noisy wick stops, Sharpe ≤ 0.50. FROZEN.
- `cci_zero_line` (internet default): 1h both sides; PF 0.80–0.87. FROZEN.

Reports: `artifacts/reports/{aly_psar_ema_rsi,financial_wisdom_dual_macd,cci_zero_line}/H0_RESULT.md`.

## Hypothesis-0 (H0) pack — Quant Tactics Donchian + Average Directional Index + Choppiness (`CgYdfwrL1VQ`)

Maximum earned readiness: `LIVE_STOP / RESEARCH_ONLY`. Evidence class: `EXPLORATORY_IN_SAMPLE` (full-history Hypothesis-0 screen, not a 2027-style exam). Data: `RESEARCH_PROXY` (engine stamp NOT GREEN). **Not a live-test candidate.**

Principal blocker: Frozen Version 2.1 gates fail. Only Ethereum 1-hour short Profit Factor (PF) 1.34 clears 1.20; that leg’s annualized Sharpe is 0.65 (Heteroskedasticity and Autocorrelation Consistent / HAC 0.69). Ethereum long PF 1.05; Bitcoin both sides PF < 1. Leakage PASS. **FROZEN** — do not search Donchian length, Average Directional Index (ADX), Choppiness, or Average True Range (ATR) multiple. Report: `artifacts/reports/quant_tactics_donchian_adx/H0_RESULT.md`.

## Live vs backtest (full VPS94 chandelier, 2026-08-25 12:16 UTC)

Maximum earned readiness remains `LIVE_STOP / RESEARCH_ONLY`. Evidence class: `FORWARD_MICRO_LIVE_RECONCILE` + `RESEARCH_PROXY`.

Principal blocker: fills are not identical (Bybit market slip vs Binance next-open + 0.05% entry slip; backtester zero exit slip). **No material missed-trade bug.** After 21 Aug 09:00 UTC through 25 Aug 11:00 UTC there were **no new chandelier signals** on Bitcoin / Ethereum / Solana, so nothing to miss. Account `Xxobster6` now 11 closed / 0 open, closed net +7.548 USDT. Do not raise size. Reports: `artifacts/reports/tsm_chandelier/by_account/Xxobster6.md` and `artifacts/reports/tsm_chandelier/by_bot/Xxobster6_{BTCUSDT,ETHUSDT,SOLUSDT}.md`.

## Live vs backtest (full VPS94 chandelier, 2026-08-21 04:58 UTC)

Maximum earned readiness remains `LIVE_STOP / RESEARCH_ONLY`. Evidence class: `FORWARD_MICRO_LIVE_RECONCILE` + `RESEARCH_PROXY`.

Principal blocker: fills are not identical (Bybit market slip vs Binance next-open + 0.05% entry slip; backtester zero exit slip). **No material signal/stop/target/exit-reason mismatch.** `/live-parity` now writes **per-account** and **per-bot** reports. Account `Xxobster6` closed net +1.945 USDT (7 closed / 3 open). Do not raise size. Reports: `artifacts/reports/tsm_chandelier/by_account/Xxobster6.md` and `artifacts/reports/tsm_chandelier/by_bot/Xxobster6_{BTCUSDT,ETHUSDT,SOLUSDT}.md`.

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
