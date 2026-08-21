# Source: The Secret Mindset (YouTube)

- **Channel:** https://www.youtube.com/@TheSecretMindset
- **Analysis tool:** `C:\projects\videoanalysis` (`config_secret_mindset.yaml`)
- **Inventory:** `C:\projects\videoanalysis\data\secret_mindset\inventory_ranked.json` (267 videos)
- **Batch 1 URLs:** `C:\projects\videoanalysis\data\secret_mindset\batch1_urls.txt` (**kept**; may improve later)
- **Batch 2 URLs:** `C:\projects\videoanalysis\data\secret_mindset\batch2_urls.txt` (next 8 ranked, excluding batch 1)
- **Batch 2 selection meta:** `C:\projects\videoanalysis\data\secret_mindset\batch2_selection.json`
- **Batch 3 URLs:** `C:\projects\videoanalysis\data\secret_mindset\batch3_urls.txt` (next 8 ranked, excluding batches 1–2)
- **Batch 3 selection meta:** `C:\projects\videoanalysis\data\secret_mindset\batch3_selection.json`
- **Batch 3 inventory:** [`BATCH3_STRATEGY_INVENTORY.md`](BATCH3_STRATEGY_INVENTORY.md)
- **Full-channel remaining (243):** `C:\projects\videoanalysis\data\secret_mindset\remaining_urls.txt`
- **Full-channel runner:** `C:\projects\videoanalysis\scripts\run_channel_until_done.py`
- **Progress:** `C:\projects\videoanalysis\data\secret_mindset\channel_progress.json` · [`CHANNEL_FULL_RUN.md`](CHANNEL_FULL_RUN.md)
- **Evidence class for later backtests:** `RESEARCH_PROXY` (Binance Last/Mark Open-High-Low-Close-Volume) until native Bybit product data is used for parity
- **Default readiness:** `LIVE_STOP / RESEARCH_ONLY` until frozen V2.1 gates pass on stitched outer Out-Of-Sample (OOS)

## Batch 1 (ranked, first 8)

| # | Video | Family hint |
|---|-------|-------------|
| 1 | [ULTIMATE Liquidity Trading Strategy (Smart Money Concepts)](https://www.youtube.com/watch?v=9P7uB4nBfyA) | Liquidity / Smart Money Concepts (SMC) |
| 2 | [Scalping … EMA RSI ADX](https://www.youtube.com/watch?v=vBM0imYSzxI) | Exponential Moving Average (EMA) + Relative Strength Index (RSI) + Average Directional Index (ADX) |
| 3 | [AGGRESSIVE Price Action Strategy](https://www.youtube.com/watch?v=0dNxenQznZY) | Price action |
| 4 | [Heiken Ashi & 50-EMA](https://www.youtube.com/watch?v=7J2djQ9C-dE) | Heikin Ashi + EMA |
| 5 | [INSANE Breakout Strategy](https://www.youtube.com/watch?v=BvUJ9upqpyI) | Breakout |
| 6 | [200 EMA Confluence](https://www.youtube.com/watch?v=imp63ZnLyck) | EMA confluence |
| 7 | [3-EMA Trading Strategy](https://www.youtube.com/watch?v=kuzYxzSxEAg) | Triple EMA |
| 8 | [RSI Day Trading Strategy](https://www.youtube.com/watch?v=Se1UJPhGnLQ) | RSI |

Pipeline reports land under `C:\projects\videoanalysis\reports\secret_mindset\`.  
Executable strategy packages are sibling folders under `strategies/` (one folder per distinct executable rule set).

**Batch 1 inventory (disposition + metrics):** [`BATCH1_STRATEGY_INVENTORY.md`](BATCH1_STRATEGY_INVENTORY.md)

## Batch 2 (next 8, in progress)

| # | Video | Family hint |
|---|-------|-------------|
| 1 | [Private EMA Heikin Ashi Scalping (HI-LO)](https://www.youtube.com/watch?v=48gxeTt-Sdw) | EMA / Heikin Ashi scalp |
| 2 | [BEST Chart Analysis System For Day Trading](https://www.youtube.com/watch?v=ZfkqKkI0YKI) | Day-trading system |
| 3 | [BEST Day Trading System … Every Morning](https://www.youtube.com/watch?v=oF_NsJLMXEs) | Morning day-trading system |
| 4 | [How SMC/ICT Secretly Copied Price Action](https://www.youtube.com/watch?v=Hq30qxOrScw) | Smart Money Concepts / price action |
| 5 | [Perfect Breakout Entries](https://www.youtube.com/watch?v=MTKAd1y1W30) | Breakout |
| 6 | [Price Action Strategy Beats 10,000 Hours](https://www.youtube.com/watch?v=owz1w37cVHs) | Price action |
| 7 | [Smart Money Triggers Stop Hunts](https://www.youtube.com/watch?v=GkNhn-k05MY) | Liquidity / stop hunts |
| 8 | [AI-Built RSI+VWAP Indicator](https://www.youtube.com/watch?v=H1x_XUEL2aY) | Relative Strength Index + Volume Weighted Average Price |

Pipeline: transcript-only (`scripts/batch_transcript_only.py --urls data/secret_mindset/batch2_urls.txt`). New packages land under `strategies/tsm_*` as rules become executable — batch 1 packages stay untouched.

## Packages created

| Folder | Source video | Status |
|--------|--------------|--------|
| [`../tsm_liquidity_sweep/`](../tsm_liquidity_sweep/) | `9P7uB4nBfyA` liquidity / SMC | `LIVE_STOP` — exploratory PF≈0.57–0.64; leakage PASS after SMC causality fix |
| [`../tsm_rsi_momentum_fib/`](../tsm_rsi_momentum_fib/) | `Se1UJPhGnLQ` RSI + Fib | `LIVE_STOP` — exploratory PF≈0.79–0.89; leakage PASS |
| [`../tsm_triple_ema_pullback/`](../tsm_triple_ema_pullback/) | `kuzYxzSxEAg` 3-EMA | `LIVE_STOP` — best cell ETH 15m PF≈0.97; leakage PASS |
| [`../tsm_ema200_channel_breakout/`](../tsm_ema200_channel_breakout/) | `imp63ZnLyck` 200 EMA channel | `LIVE_STOP` — PF≈0.80–0.91; leakage PASS |
| [`../tsm_rsi_adx_ema_scalp/`](../tsm_rsi_adx_ema_scalp/) | `vBM0imYSzxI` RSI+ADX+EMA | `LIVE_STOP` — PF≈0.03–0.16 (stop inside bar noise); leakage PASS |
| [`../tsm_london_opening_channel/`](../tsm_london_opening_channel/) | `BvUJ9upqpyI` London open channel | `LIVE_STOP` — BTC PF≈0.62 / ETH PF≈0.84; leakage PASS |
| [`../tsm_pressure_zone/`](../tsm_pressure_zone/) | `0dNxenQznZY` pressure zone | `LIVE_STOP` — nested 1d OOS PF≈1.24 but Sharpe/fold gates fail; leakage PASS |
| [`../tsm_heikin_ashi_ema50/`](../tsm_heikin_ashi_ema50/) | `7J2djQ9C-dE` HA wedge + EMA50 | `LIVE_STOP` — nested 1h OOS PF≈0.82 (abandon H0); leakage PASS |
| [`../tsm_hilo_ha_adx/`](../tsm_hilo_ha_adx/) | `48gxeTt-Sdw` HI-LO channel + HA + ADX (batch 2) | FAIL exploratory PF≈0.63–0.84 |
| [`../tsm_vwap_rsi/`](../tsm_vwap_rsi/) | `H1x_XUEL2aY` VWAP + RSI (batch 2) | FAIL 1h PF≈0.81–0.91 |
| [`../tsm_breakout_score/`](../tsm_breakout_score/) | `MTKAd1y1W30` breakout score (batch 2) | ABANDON H0 (n≤3) |
| [`../tsm_vwap_outside/`](../tsm_vwap_outside/) | `ZfkqKkI0YKI` VWAP outside candle (batch 2) | FAIL 15m PF≈0.56–0.67 |
| [`../tsm_failed_breakout/`](../tsm_failed_breakout/) | `GkNhn-k05MY` failed breakout trap (batch 2) | FAIL PF≈0.70–0.95 |
| [`../tsm_impulse_volume/`](../tsm_impulse_volume/) | `owz1w37cVHs` impulse + volume (batch 2) | nested 4h OOS PF≈1.08 — FAILED_GATES |
| [`../tsm_vwap_sd/`](../tsm_vwap_sd/) | `oF_NsJLMXEs` VWAP + S/D proxy (batch 2) | FAIL PF≈0.62–0.93 |
| [`../tsm_flag_ema2155/`](../tsm_flag_ema2155/) | `rThEVFW75Ew` flag + 21/55 EMA (batch 3) | FAIL PF≈0.74–0.94 |
| [`../tsm_pivot_bb/`](../tsm_pivot_bb/) | `_8q3ZJ5afFA` monthly pivot + BB (batch 3) | mixed ETH 1d PF≈1.33 / BTC fail |
| [`../tsm_engulf_demand/`](../tsm_engulf_demand/) | `UQR4rM9L6Fg` engulf at demand (batch 3) | nested 4h OOS PF≈1.56 — FAILED_GATES (sharpe) |
| [`../tsm_ema20_200/`](../tsm_ema20_200/) | `yPbUn3Wuh98` EMA 20/200 (batch 3) | FAIL PF≈0.90–1.07 |
| [`../tsm_ema2155_ribbon/`](../tsm_ema2155_ribbon/) | `En2ZIfAyhBg` 21/55 ribbon (batch 3) | FAIL PF≈0.84–0.96 |
| [`../tsm_adx_dmi_obv/`](../tsm_adx_dmi_obv/) | `4rn1vw3kGuU` ADX/DMI+OBV (batch 3) | sparse/mixed |
| [`../tsm_macd_trend/`](../tsm_macd_trend/) | `S2HaCa0b-bY` MACD trend (continuation) | FAIL exploratory PF≈0.89–0.94 |
| [`../tsm_vol_climax/`](../tsm_vol_climax/) | `Dv9o9tCiqx8` volume climax (continuation) | ABANDON H0 — no_signals |
| [`../tsm_chandelier/`](../tsm_chandelier/) | `HzkU6cbcI1o` Chandelier/ATR (continuation) | **best TSM OOS** — PENDING_DSR_BOOTSTRAP_STRESS |
