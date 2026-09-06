# Hypothesis-0 and related tests — registry

**As of:** 2026-09-04 (QQE, Squeeze Momentum, Connors RSI-2)  
**Maximum earned readiness (all video recipes and The Secret Mindset (TSM) packs except authorized micro-live):** `LIVE_STOP / RESEARCH_ONLY`  
**Evidence class for every H0 row below:** `EXPLORATORY_IN_SAMPLE` (full-history public-recipe screen). **Not** a 2027-style exam. Data venue: `RESEARCH_PROXY`. Engine stamp **NOT GREEN**.  
**Live-test candidate from this registry:** **none** (chandelier on VPS94 is a separate user-authorized min-size experiment, not a Frozen Version 2.1 pass).

Hunting agents: install `C:\projects\BASE CURSOR\TRADING_BOT_CURSOR_RULES_V2.zip`, read `docs/project_memory/IN_SAMPLE_VS_OOS.md`, check `INSTALLED_STANDARD_HASHES.md`. A real search needs `RESEARCH_GENERATION_FREEZE.md` filled **before** exam Profit Factor (PF). Current freeze: **NO SEARCH OPEN**.

This file is the index of **what was tested, how, and what is still allowed to explore**. Per-pack numbers live in `artifacts/reports/<pack>/H0_RESULT.md` or `baseline_h0.json`. Channel theory notes: `docs/project_memory/KROWN_NOTES.md`.

---

## How every hypothesis-0 (H0) pack is tested

1. **Freeze the public recipe first.** Captions / stated rules go into `strategies/<pack>/STRATEGY.md` *before* looking at our Profit Factor (PF). Defaults that the video left blank are written down (not searched). Paid app-only rules are skipped.
2. **Causality.** Close-based signals fill at the **next bar open**. Higher-timeframe features use only **completed, lagged** candles (`engine.features.lag_htf_to_ltf`). No negative shifts, no full-history scalers.
3. **Unit tests.** Warm-up mask, truncation (future bars must not change earlier signals), long vs short / short_mirror side separation. Vectorized NumPy/pandas features.
4. **Leakage audit.** `run_leakage.py` on Open-High-Low-Close plus strategy columns. Omit take-profit prices from the feature keep-list. Hard-fail leakage blocks the baseline.
5. **Full-history baseline.** Shared runner `strategies/common/h0_baseline.py` → `tradesim.run_backtest`. Typical window **2020-01-01** through **2026-04** or **2026-08**. Symbols **BTCUSDT** and **ETHUSDT** unless the recipe is symbol-specific. Venue costs: Bybit-style taker **0.055%** per fill; sizing is smallest legal quantity unless the pack says otherwise. **EXEC-021 (1 Sep 2026):** take-profit/stop and resting limits walk **1-minute** bars from the fillable bar. A print before the limit fill is not a win. Bitcoin/Ethereum 1-minute was backfilled 2020→2026 (previously only August 2026). Fleet report: `artifacts/reports/exec021_fleet/FLEET_RESULT.md`. Coverage below 95% is skipped, not silently stop-first.
6. **Sides.** Long-only sources also get a **separate** `short_mirror` report. Both-sides recipes report long and short **separately**. Metrics are **never pooled** across sides for a gate.
7. **One pre-registered improvement only**, and only from the source’s own words, frozen **before** our numbers (example: Krown paper-cut). Reverse long/short is that separate leg, not a search.
8. **What this is not.** It is **not** nested outer Out-Of-Sample, **not** a 2027-style exam, not a green engine stamp, not live authorization. Label: `EXPLORATORY_IN_SAMPLE`. After the full-history numbers are viewed, **do not search** lengths, thresholds, day-of-week, or “winners” from the creator’s on-video grid.

**Frozen Version 2.1 (shadow-ready, historical):** ≥5 outer folds, ≥10 trades per gating fold, ≥50 pooled Out-Of-Sample trades, pooled PF ≥ 1.20, annualized daily mark-to-market Sharpe ≥ 1.00, Heteroskedasticity and Autocorrelation Consistent (HAC) Sharpe ≥ 0.75, plus drawdown / stress / no liquidation. Full-history PF even above 1.20 **does not** earn shadow or live.

---

## Video recipes — tested and frozen

| Pack | Source video | What we coded | Leakage | Best full-history PF (leg) | Best Sharpe (ann.) | Action |
|------|----------------|---------------|---------|----------------------------|--------------------|--------|
| `algovibes_eth_dip` | `pWm4fFsJXt4` | 1h/4h close-to-close dip ≤ −1%, +0.5% target or 5-bar hold, 3% stop | (see pack) | 0.58 BTC 1h | −2.40 | **FROZEN FAIL** |
| `tradingrush_bb_breakout` | `8_QWC2KzRUA` | Close above Bollinger 20±2, signal-bar low stop, 1.5R, 15m+1h | PASS | 0.96 ETH 1h | −0.18 | **FROZEN FAIL** |
| `tradingrush_macd_cross` | `B7jrlVeis6k` | MACD 12/26/9 cross below zero + 200 SMA, 15m+1h | PASS | 0.70 ETH 1h | −1.02 | **FROZEN FAIL** |
| `coinquant_regime_adx` | `pD1gDYnLRu0` | ADX regime + regression + Bollinger; **sides pooled** | PASS | 1.33 BTC 1h | 0.71 | **FROZEN / contaminated** — do not optimize |
| `monday_range_sweep` | `BFdEPlNSaps` | 1h close outside Monday range then back inside (trigger 1) | PASS | 0.85 ETH 1h | −0.25 | **FROZEN FAIL** (pooled sides) |
| `keltner_channel_breakout` | `DhnwMO6bjQg` | EMA20, ATR20×2, stop at middle; long + short_mirror; 4h+1d | PASS | **3.44 BTC 1d long** (n=23) | 1.00 | **FROZEN** — sparse daily; no nested Out-Of-Sample |
| `turtle_donchian_s1` | `dk9c7jC3VO4` | System 1 prior 20-day break; daily both sides | PASS | 1.61 ETH 1d long (n=32) | 0.25 | **FROZEN** — sparse; do not add System 2 / pyramid on this sample |
| `quant_forge_mtf_ema_pullback` | `DkTJiMHZLFE` | 4h EMA200 slope + 1h EMA20 pullback, 1.2×ATR stop, 1R | PASS | 0.70 BTC 1h long | −2.02 | **FROZEN FAIL** |
| `heikin_ashi_bb_stoch` | `qP2XkQcr2eU` | Heikin Ashi × Bollinger × Stochastic RSI, 1h both sides | PASS | 0.96 ETH 1h short | −0.14 | **FROZEN FAIL** |
| `quant_tactics_donchian_adx` | `CgYdfwrL1VQ` | Donchian 20 + EMA50 + ADX14>20 + Choppiness<40, 3×ATR stop | PASS | 1.34 ETH 1h short | 0.65 | **FROZEN** — only one leg PF≥1.20; Sharpe 0.65 |
| `aly_psar_ema_rsi` | `RdHzNY0K2ws` | 4h Parabolic SAR + EMA200 + RSI>50, swing stop 1.5R | PASS | 1.17 BTC 4h long | 0.35 | **FROZEN FAIL** (reverse included) |
| `financial_wisdom_dual_macd` | `Gzl43lj2tS4` | Weekly+daily MACD 12/26/9; wick stop; long + short_mirror | PASS | 1.83 ETH 1d short_mirror (n=60) | 0.50 | **FROZEN** — sparse, noisy wick stops |
| `cci_zero_line` | internet default | CCI 14 zero-line cross, 1h both sides | PASS | 0.87 ETH 1h short | −0.91 | **FROZEN FAIL** |
| `krown_ema5_daily` | `C0wM-iKfwaI` | Daily close vs 5 EMA; stop = signal-bar EMA (incomplete vs overlay) | PASS | H0 1.33 / paper-cut **1.47** BTC long | 0.38 / 0.46 | **FROZEN** — do not search EMA length or Friday-skip |
| `krown_rsi_momentum_burst` | `hTcz81O2w-o` | 1h RSI fresh cross 70 + SMA200 + lagged 4h/daily RSI>50; 24h time exit | PASS | 1.26 ETH 1h long | 0.53 | **FROZEN** — do not copy the 576-variant search |
| `krown_bbwp_squeeze` | `kcMnnQr1VFg` | 4h BBWP squeeze-release (cross 25) + SMA 200; 2×ATR / 2R | PASS | 1.00 ETH 4h long | −0.01 | **FROZEN FAIL** |
| `ema20_50_cci` | `RFMM8WkLXVI` | 1h EMA 20/50 cross + EMA 200 + CCI ±100; 1×ATR / 1.5R | PASS | 0.92 ETH 1h short | −0.13 | **FROZEN FAIL** |
| `ichimoku_chikou` | `EpFv0L0sz9c` | 4h Tenkan/Kijun alignment + Chikou candle break; Kijun stop 2R | PASS | 1.21 ETH 4h short | 0.38 | **FROZEN FAIL** — do not search 9/26/52 |
| `ichimoku_double` | `EpFv0L0sz9c` HTF tip | Lagged daily cloud/TK bias + same 4h Chikou entry | PASS | 1.17 ETH 4h short | 0.20 | **FROZEN FAIL** — daily filter made it worse |
| `roman_hma_cross` | `zZQNhDGSUEI` | HMA 16 close-cross; stop at signal-bar HMA; 4h+1d | PASS | 1.09 ETH 4h short_mirror | 0.16 | **FROZEN FAIL** — 55%+ same-bar stops |
| `turkish_express` | `J3be7tlxB6E` | EMA200 + MavilimW + IFT −0.5 + 10-bar swing 3R; 15m+1h | PASS | 1.14 ETH 1h short | 0.38 | **FROZEN FAIL** |
| `turkish_express_hma` | mix `J3be7tlxB6E`+`zZQNhDGSUEI` | Same Turkish entries with HMA 16 instead of EMA200 | PASS | 1.10 ETH 1h short | 0.30 | **FROZEN FAIL** — mix worse than EMA200 |
| `quant_tactics_st_ema200` | `53yqW60SDPk` | SuperTrend 8×4 + EMA200 + 1.5×ATR; 4h both sides | PASS | **1.95 ETH 4h long** (n=103) | 0.98 | **FROZEN** — Sharpe 0.98; not nested Out-Of-Sample; not a chandelier retune |
| `double_bb_range_break` | `0cn9mAnOoX0` | Inner 0.5-sigma range then prior-bar break; 1.5R; 15m+1h | PASS | 0.81 ETH 1h short | −1.38 | **FROZEN FAIL** — fee grind |
| `halftrend_ema_atr` | `jjgeQUnZyz0` | Everget HalfTrend 2/2 + EMA 60 + 1.5/3 ATR 14; 15m+1h | PASS | 0.98 ETH 1h long | −0.08 | **FROZEN FAIL** — do not add extra TradeSmart filters |
| `qqe_mod_zero` | `N3A8g083dWY` | QQE MOD RSI 6 / SF 5 zero-cross + EMA 200 + 10-bar 1.5R; 15m+1h | PASS | 0.95 ETH 1h long | — | **FROZEN FAIL** |
| `lazybear_squeeze_mom` | `GXqXYW12x_I` | LazyBear histogram sign, ATR 14×1.5, 1R; 1h+1d | PASS | 1.23 ETH 1d short (n=47) | 0.23 | **FROZEN FAIL** — 1h loses; daily sparse |
| `connors_rsi2` | Connors public / `AMEO6VkZujY` | RSI 2 < 5, SMA 5 target, 2×ATR stop; 1h+1d long + short_mirror | PASS | 0.99 BTC 1d long | — | **FROZEN FAIL** — WR high, PF < 1 |
| `elder_impulse` | Elder public / `JOZZrfFRWv8` | EMA 13 + MACD hist 12/26/9 color bars; 2×ATR / 1.5R; 1h+1d | PASS | 1.23 ETH 1d short (n=82) | 0.31 | **FROZEN FAIL** — 1h loses; daily sparse |
| `kst_cross` | Pring public / `9YhQq9CkNJc` | KST 10/15/20/30 vs SMA 9; 2×ATR / 1.5R; 1h+1d | PASS | 1.17 BTC 1d long (n=52) | 0.20 | **FROZEN FAIL** |
| `guppy_mma` | Guppy public / `gjW0x7UJl-c` | EMA ribbon 3–15 vs 30–60 full separation; 2×ATR / 1.5R; 1h+1d | PASS | 1.78 ETH 1d short (n=23) | 0.46 | **FROZEN FAIL** — 23 trades |
| `schaff_trend_cycle` | Schaff public / `coiOSMR7B4M` | STC 23/50/10 cross 25/75; 2×ATR / 1.5R; 1h+1d | PASS | 1.14 ETH 1d short (n=59) | 0.16 | **FROZEN FAIL** |
| `vortex_cross` | Vortex public 14 | VI+ / VI− cross; 2×ATR / 1.5R; 1h+1d | PASS | 1.02 BTC 1d long (n=60) | 0.02 | **FROZEN FAIL** |

Paper-cut H0b for Krown 5 EMA: skip `|close−EMA| ≤ 0.25 × Average True Range (ATR) 14`. Pre-registered from his “paper cut” comment. Same-bar shakeouts dropped from ~64% to ~42%; still fails Sharpe.

**Attractive-looking numbers that are not candidates:** Keltner daily PF 3.44 (23 trades), Turtle PF 1.61 (32 trades), Dual MACD PF 1.83 (60 trades, WR ~18%), CoinQuant PF 1.33 (pooled sides, contaminated), SuperTrend+EMA200 Ethereum 4-hour long PF 1.95 (103 trades, Sharpe 0.98, full-history only). Sparse or pooled or full-history only.

---

## The Secret Mindset (TSM) family — tested

Same H0 engine. Source: TSM YouTube / continuation packs under `strategies/tsm_*`. Headline table: `artifacts/reports/tsm_all_metrics.json`.

| Pack | Best PF (this registry) | Note |
|------|-------------------------|------|
| `tsm_chandelier` | 1.52 ETH 1h (Sharpe 1.31); BTC 1h PF 1.33 Sharpe 0.89; **15m both fail** | Historical 1h looked best. **Micro-live** on VPS94 / Xxobster6 min size (BTC, ETH, SOL). Fill parity **fails** (Bybit market slip vs Binance next-open + 0.05% entry slip; backtester zero exit slip). Do not raise size. |
| `tsm_adx_dmi_obv` | 2.93 BTC 1d (n=6) | Sparse; not a gate pass |
| `tsm_engulf_demand` | 1.57 BTC 4h (n=71) | Full-history only |
| `tsm_pressure_zone` | 1.41 BTC 1d | Full-history only |
| `tsm_pivot_bb` | 1.33 ETH 1d | Full-history only |
| `tsm_impulse_volume` | 1.15 BTC 4h | Below PF 1.20 / Sharpe 1.00 |
| `tsm_ema20_200` | 1.07 BTC 4h | Fail |
| `tsm_heikin_ashi_ema50` | 1.00 BTC 1h | Fail |
| `tsm_triple_ema_pullback`, `tsm_ema2155_ribbon`, `tsm_failed_breakout`, `tsm_flag_ema2155`, `tsm_macd_trend`, `tsm_vwap_sd`, `tsm_ema200_channel_breakout`, `tsm_vwap_rsi`, `tsm_rsi_momentum_fib`, `tsm_hilo_ha_adx`, `tsm_london_opening_channel`, `tsm_vwap_outside`, `tsm_liquidity_sweep`, `tsm_rsi_adx_ema_scalp` | PF < 1 | **FROZEN FAIL** — do not retune |
| `tsm_breakout_score` | 0 (n=3) | No edge / insufficient trades |
| `tsm_vol_climax` | no_signals on 1h/4h BTC/ETH | Recipe produced no executable signals in H0 |

Do not least-squares-retune losing TSM packs on this inspected history.

---

## Smart Money Concepts (SMC) confluence / killzone

Gen1–Gen4 **abandoned for live**. Gen2 exact re-run (freeze `2c65ce212a96ecb16e6519b55a8eaa39dacdf51cac5bc6a4e2d3797f1dd4af3a`): net −392, PF 0.66, 5/5 folds red. Any new SMC work must be a **new preregistered generation** with a different economic hypothesis.

---

## EXEC-021 fleet (1 Sep 2026)

Correct 1-minute fill clock on all 42 packs with `signals.py`. Full table: `artifacts/reports/exec021_fleet/FLEET_RESULT.md`. **No new live-test candidate.** Zero not-live rows with ≥50 trades, Profit Factor ≥ 1.20, and Sharpe ≥ 1.00. Live chandelier 1-hour market-match: Ethereum PF 1.60 Sharpe 1.41; Bitcoin PF 1.29 Sharpe 0.81; Solana PF 1.27 Sharpe 0.67. 15-minute chandelier loses. Do not search parameters on that file.

## Live vs backtest (chandelier only)

Evidence class: `FORWARD_MICRO_LIVE_RECONCILE` + `RESEARCH_PROXY`. Reports: `artifacts/reports/tsm_chandelier/by_account/Xxobster6.md`. Principal blocker remains **fill model**, not missed signals. No new video recipe is authorized for VPS.

---

## Video analysis pipeline (running 2026-09-04)

Pause file removed. Keep-alive restarted. **41 unique** user-queue videos pending captions (18 added this session: Connors Relative Strength Index 2, Know Sure Thing, Elder Impulse, Guppy, Quantitative Qualitative Estimation, Aroon, linear regression). SuperTrend+Average True Range+Average Directional Index (`tQfZbC43uJc`) — still **not** a chandelier retune. Coppock remains incomplete. Seed-scout auto-resume is still blocking the user-URL worker; harvest is in the file, captions are not yet flowing.

---

## Ideas worth exploring (new hypotheses only)

These are **not** permission to search frozen packs. Each would need a written freeze *before* any backtest.

1. **Engine conformance GREEN** (tradesim fixtures) so later H0 numbers are quotable. This is infrastructure, not alpha.
2. **Chandelier live accounting:** model Bybit StopLoss as taker + slip; keep size at the 5% wallet-equity rule until fills reconcile. Operational, not a parameter search.
3. **Aroon** — public 14/14 defaults, only with a written stop freeze before Profit Factor.

Williams Alligator stack (`HmKh1hqvU5Y` / `1mzuNXv_Lss`) remains low priority (Freqtrade optimization / too many thresholds). Coppock Curve (`tnUZLLUGpo8`) captions were **not** extractable as a complete crypto recipe. SuperTrend+ADX (`tQfZbC43uJc`) may be packaged as a **new** public recipe after captions; it is **not** a chandelier retune and is **not** a retune of `quant_tactics_st_ema200`. Hull, Double Bollinger, HalfTrend, QQE MOD, LazyBear Squeeze, and Connors RSI-2 are **tested and frozen**.

### Explicitly not worth exploring on current evidence

- Friday-skip / day-of-week on Krown 5 EMA (he mined it on camera).
- Any of Krown’s 576 / 1,600 / 888 on-video search winners.
- HalfTrend amplitude 6 / channel 2.4, extra 50/100/200 Exponential Moving Averages, Chandemo, two-candle wait, or 5-minute on `halftrend_ema_atr`.
- QQE 5-minute, extra Exponential Moving Averages from `VeyiMLqMifg`, or SuperTrend+QQE 100× clips on `qqe_mod_zero`.
- Squeeze Momentum 30-minute, length search, or Krown BBWP settings on `lazybear_squeeze_mom`.
- Connors RSI threshold 10, 15-minute, or “200,000 trades” RSI winners on `connors_rsi2`.
- Elder Impulse length search or 15-minute on `elder_impulse` because one daily short Profit Factor was 1.23.
- Know Sure Thing Rate of Change search or Bollinger add-on on `kst_cross` because Bitcoin daily long Profit Factor was 1.17.
- Guppy ribbon length search, Relative Strength Index add-on, or 15-minute on `guppy_mma` because one 23-trade daily short Profit Factor was 1.78.
- Schaff Trend Cycle 23/50/10 or 25/75 search, SuperTrend mix, or 15-minute on `schaff_trend_cycle`.
- Vortex length 9/21, Average Directional Index add-on, or 15-minute on `vortex_cross`.
- SuperTrend + Donchian as a chandelier retune.
- SuperTrend 8/4 vs 10/3 or 1-hour on `quant_tactics_st_ema200` because Ethereum Sharpe was 0.98.
- Double Bollinger 123-pattern add-on or 0.5/3.0 search on `double_bb_range_break`.
- Hull length 140 (on-video heatmap) or Average True Range stop on `roman_hma_cross`.
- Inverse Fisher +0.5 short “fix”, 5-minute crypto, or Reward:Risk search on `turkish_express` / `turkish_express_hma`.
- CoinQuant ADX re-optimization; TradingRush MACD/BB retunes; Algovibes dip thresholds.
- Turtle System 2, pyramiding, or Keltner length search on the inspected sample.
- Paid Krown / Caretaker scripts (HPDR, HPAS, Caretaker RSI).
- CCI+RSI confluence videos (`C7SbYLKLeyk` and friends) — adjacent to frozen CCI zero-line and EMA+CCI; do not package as a “fix”.
- Ichimoku 9/26/52 retune, weekly+daily, 1-hour execution, or TradingView dual-cloud 10/30/60 on the inspected sample.
- SMC Gen2–4 retune.

### Captioned but not packaged

- Krown candlesticks (`8MvxK_nxO-0`) — beginner patterns, not a full executable recipe.
- Krown daily 200 SMA rejection (`_92fXlj7WyU`) — narrative, not mechanical.
- Discovery near-misses: discretionary flags (`I9WNbcrOoqI`), Alligator without take-profit (`hn9o9FN8VP0`), “Slope is Dope” extreme 90%/60% (`UvS3ixWG2zs`). Only package if rules become fully specified without a search.
- HalfTrend extra TradeSmart filters (`jjgeQUnZyz0`) — base pack `halftrend_ema_atr` is frozen fail; never package the add-on chapter as a “fix”.

---

## Pointers

- Practice vs exam: `docs/project_memory/IN_SAMPLE_VS_OOS.md`
- Pack zip: `C:\projects\BASE CURSOR\TRADING_BOT_CURSOR_RULES_V2.zip`
- Installed hashes: `docs/project_memory/INSTALLED_STANDARD_HASHES.md`
- Search freeze (none open): `docs/project_memory/RESEARCH_GENERATION_FREEZE.md`
- Per-pack reports: `artifacts/reports/<pack>/`
- Metrics canvas (video H0 legs): Cursor canvas `video-h0-metrics`
- Discovery candidate scan (25 Aug 2026): `artifacts/reports/discovery_recipe_scan_20260825.md`
- Current sitrep: `docs/project_memory/CURRENT_STATE.md`
