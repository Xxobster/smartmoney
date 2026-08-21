# The Secret Mindset — Batch 1 strategy inventory

**Channel:** https://www.youtube.com/@TheSecretMindset  
**Batch date:** 2026-08-08 / 2026-08-09  
**Default readiness:** `LIVE_STOP / RESEARCH_ONLY`  
**Evidence class:** `RESEARCH_PROXY` (Binance Open-High-Low-Close-Volume + Bybit-style costs)  
**Engine stamp:** NOT GREEN — full-history numbers are diagnostic only  
**Video tool:** `C:\projects\videoanalysis` (`config_secret_mindset.yaml`)  
**Packages root:** `D:\projects\smartmoney\strategies\`

## Disposition legend

| Tag | Meaning |
|-----|---------|
| `ABANDON_H0` | Exploratory H0 fails badly after costs; do not grid Take-Profit/Stop-Loss |
| `WATCH` | Weak / near-flat; no nested Out-Of-Sample (OOS) yet |
| `WF_CANDIDATE` | Full-history Profit Factor (PF) ≥ 1 on at least one cell; fixed-H0 walk-forward preregistered |
| `FAIL` | Clear post-cost underperformance on explored cells |

## Batch 1 videos → packages

| # | Video ID | Title (short) | Package | Disposition | Best exploratory cell |
|---|----------|---------------|---------|-------------|------------------------|
| 1 | `9P7uB4nBfyA` | Liquidity / Smart Money Concepts | `tsm_liquidity_sweep` | `FAIL` | BTC 15m PF 0.57 / WR 30.5%; ETH PF 0.64 / WR 30.9% |
| 2 | `vBM0imYSzxI` | RSI + ADX + EMA scalp | `tsm_rsi_adx_ema_scalp` | `ABANDON_H0` | Noise stops (~87% entry-bar exits); PF 0.03–0.16 |
| 3 | `0dNxenQznZY` | Pressure zone (shadow overlap) | `tsm_pressure_zone` | `WATCH` after OOS | Full-hist 1d PF>1; nested OOS PF 1.24 but Sharpe/fold gates fail |
| 4 | `7J2djQ9C-dE` | Heikin Ashi rising wedge + EMA50 | `tsm_heikin_ashi_ema50` | `ABANDON_H0` after OOS | Nested OOS PF 0.82 / net −65; captions used (media flaky) |
| 5 | `BvUJ9upqpyI` | London opening channel | `tsm_london_opening_channel` | `FAIL` | BTC 1h PF 0.62 / WR 57.2%; ETH PF 0.84 / WR 61.9% |
| 6 | `imp63ZnLyck` | 200 EMA channel breakout | `tsm_ema200_channel_breakout` | `FAIL` | PF 0.80–0.91 |
| 7 | `kuzYxzSxEAg` | Triple EMA pullback | `tsm_triple_ema_pullback` | `WATCH` | Closest fail: ETH 15m PF 0.97 / WR 41.6% |
| 8 | `Se1UJPhGnLQ` | RSI + Fib momentum | `tsm_rsi_momentum_fib` | `FAIL` | BTC 15m PF 0.79 / WR 36.5%; ETH PF 0.89 / WR 36.6% |

## Executable H0 one-liners

1. **Liquidity sweep** — sweep + reclaim on 15m with higher-timeframe bias; RR 2.0  
2. **RSI+ADX+EMA** — RSI(3) extremes + ADX(5)>30 + EMA50; RR 1.0; 5m/15m  
3. **Pressure zone** — 3 overlapping shadows → zone; enter close through zone; stop at formation extreme; RR 2.0; EMA50 filter; **1d WF**  
4. **Heikin Ashi wedge** — rising/falling wedge on HA + break vs EMA50; TP max(2R, width); **1h WF**  
5. **London channel** — UTC hour-7 range; break after 08:00; EMA200 filter; TP = width  
6. **EMA200 channel** — EMA of highs/lows channel; break + retest; RR 3.0  
7. **Triple EMA** — EMA20/100/200 align; bounce at EMA100; RR 2.0  
8. **RSI Fib** — RSI arm 70/30 → Fib pullback rejection; EMA50; RR 2.0  

## Leakage

All eight packages: leakage audit **PASS** on the feature matrix used for each H0 (stops/targets/zone geometry excluded where required).

## Validation policy (batch 1 freeze)

- Nested walk-forward is **only** preregistered for:
  - `tsm_pressure_zone` @ **1d**
  - `tsm_heikin_ashi_ema50` @ **1h**
- No Take-Profit / Stop-Loss / window grids after viewing outer OOS.
- Other families remain `LIVE_STOP` without OOS promotion.
- Batch 2 videos: **not started** (validation bottleneck first).

## Nested outer Out-Of-Sample (OOS) — fixed H0 (2026-08-09)

Configs hashed at preregistration; `trial_budget_total: 1`; no parameter search.

| Generation | Stitched trades | Pooled PF | Net PnL | Sharpe ann* | +eligible folds | Readiness | Principal blocker |
|------------|----------------:|----------:|--------:|------------:|----------------:|-----------|-------------------|
| `tsm_pressure_zone_1d_h0_wf_20260809` | 137 | **1.24** | +44.1 | 0.30 | 60% (need 80%) | `LIVE_STOP / RESEARCH_ONLY_FAILED_GATES` | Sharpe (& fold consistency / HAC) |
| `tsm_heikin_ashi_ema50_1h_wf_20260809` | 566 | 0.82 | −64.7 | −0.86 | 20% | `LIVE_STOP / RESEARCH_ONLY_FAILED_GATES` | net PnL positive (also PF/Sharpe/folds) |

\*Mean of per-symbol stitched daily Mark-To-Market Sharpe (not a substitute for one shared-wallet curve).

**Pressure zone note:** last outer fold (esp. BTC) dominates PnL — concentration risk; do **not** retune exits on this OOS. Next allowed move is a **new** preregistered economic redesign or abandon, not a Take-Profit/Stop-Loss grid.  
**Heikin Ashi note:** fixed H0 **fails** nested OOS — treat as abandoned at this H0 unless a new hypothesis is preregistered.

DSR / bootstrap / PBO / cost-stress were **not** run (cannot earn `SHADOW_READY` from partial Gate B alone).

## Artifact pointers

| Kind | Path |
|------|------|
| Baselines | `artifacts/reports/tsm_*/baseline_h0.json` |
| Pressure 1d full trades | `artifacts/reports/tsm_pressure_zone/1d_full/` |
| WF configs | `config/search_space_tsm_pressure_zone_1d.yaml`, `config/search_space_tsm_heikin_ashi_ema50_1h.yaml` |
| Video reports | `C:\projects\videoanalysis\reports\secret_mindset\` |
| Ranked inventory | `C:\projects\videoanalysis\data\secret_mindset\inventory_ranked.json` (267 videos) |
