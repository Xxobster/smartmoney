# Discovery recipe scan — hypothesis-0 packaging candidates

**Date:** 2026-08-25  
**Source:** `C:\projects\videoanalysis\reports\discovery\video_*_deep.json` (264 files)  
**Filter:** complete public entry + exit + indicators; crypto / Bitcoin (BTC) / Ethereum (ETH) preferred; reproducible `YES` or `MOSTLY`; skip vague motivational content.

## Excluded (already packaged / frozen)

| video_id | family |
|---|---|
| `pWm4fFsJXt4` | Algovibes Ethereum dip |
| `8_QWC2KzRUA` | TradingRush Bollinger Band breakout |
| `B7jrlVeis6k` | TradingRush Moving Average Convergence Divergence (MACD) |
| `pD1gDYnLRu0` | CoinQuant Average Directional Index (ADX) |
| `BFdEPlNSaps` | Monday range |
| `DhnwMO6bjQg` | Keltner (packaged separately) |

Also demoted (same-family, not in NEW top 8):

- `r55TZ-0BkoM`, `MrCWRS9npFE` — TradingRush MACD entry variants (breakeven / Parabolic Stop and Reverse trail)

## Known best (excluded from NEW list)

**`DhnwMO6bjQg`** — Roman / AlgoTrading Strategies — *Keltner Channel Breakout* — reproducible **YES** — BTC/USDT — Daily / 4H / 2H — long_only — close above upper Keltner → exit close below middle — parameters explicit via sensitivity grid — blockers: no hard stop-loss (Stop Loss); exit is indicator-based.

---

## Ranked NEW candidates (up to 8)

### 1. `dk9c7jC3VO4` — Turtle Donchian (best packaging fit)

| field | value |
|---|---|
| **Title** | I Coded the $100M Turtle Trading Strategy. Does It Still Work? |
| **Channel** | Ssmurf gg |
| **Reproducible** | MOSTLY |
| **Symbols** | Bitcoin, Ethereum (also equity Exchange-Traded Funds) |
| **Timeframes** | Daily |
| **Sides** | both |
| **Parameters** | explicit (20 / 55 Donchian; 10 / 20 exits; 2× Average True Range stop) |
| **Entry / exit (public)** | System 1: break prior 20-day high/low; System 2: 55-day. Exit System 1 long on 10-day low (mirror short); System 2 on 20-day channel. Stop = 2× Average True Range (ATR). |
| **Blockers** | Take-profit is channel exit only (no fixed Reward:Risk); multi-asset video — freeze BTC/ETH for hypothesis-0 |

### 2. `DkTJiMHZLFE` — Multi-timeframe Exponential Moving Average pullback + ATR

| field | value |
|---|---|
| **Title** | ChatGPT Built the Most Sophisticated Bitcoin Strategy I've Ever Seen… |
| **Channel** | Quant Forge |
| **Reproducible** | MOSTLY |
| **Symbols** | BTC |
| **Timeframes** | 4-hour + 1-hour |
| **Sides** | both (short conditions marked AMBIGUOUS in extractability; rules are mirror-stated) |
| **Parameters** | explicit (200 Exponential Moving Average 4H, 20 Exponential Moving Average 1H, ATR 14, stop 1.2× ATR) |
| **Entry / exit (public)** | Trend filter: price vs 4H 200 Exponential Moving Average + slope; pullback to 1H 20 Exponential Moving Average; confirmation candle with rising volume. Exit: take 50% at 1R; trail remainder with 1H 20 Exponential Moving Average. |
| **Blockers** | “Exponential Moving Average sloping” needs a fair default (e.g. EMA_t > EMA_{t-n}); optional “compressed ATR” filter ambiguous |

### 3. `qP2XkQcr2eU` — Heikin Ashi × Bollinger Bands × Stochastic Relative Strength Index

| field | value |
|---|---|
| **Title** | Ultimate Heikin Ashi x Bollinger Bands Trading Strategy \| Cryptocurrency Trading |
| **Channel** | Crypto_Fox |
| **Reproducible** | MOSTLY |
| **Symbols** | Bitcoin |
| **Timeframes** | 1 hour |
| **Sides** | both |
| **Parameters** | explicit (Exponential Moving Average 40, Simple Moving Average 50, Stochastic Relative Strength Index 20/80) |
| **Entry / exit (public)** | Trend: EMA40 vs SMA50. Long: touch lower Bollinger Band + Stochastic Relative Strength Index &lt; 20 + reclaim inside band + Heikin Ashi flips green (mirror short). Exit on opposite Heikin Ashi color. Stop at extreme of touch candle. |
| **Blockers** | No fixed take-profit (color exit only); Bollinger length/std need fair defaults if not stated; distinct from abandoned The Secret Mindset Heikin Ashi wedge family |

### 4. `CgYdfwrL1VQ` — Donchian + ADX + Choppiness (ETH)

| field | value |
|---|---|
| **Title** | Donchian Channel Strategy made 140% Profit! (Full Tutorial) |
| **Channel** | Quant Tactics |
| **Reproducible** | MOSTLY |
| **Symbols** | ETH |
| **Timeframes** | 1 hour |
| **Sides** | both |
| **Parameters** | need fair defaults (Donchian period, Exponential Moving Average 50 stated; ADX&gt;20, Choppiness&lt;40 explicit) |
| **Entry / exit (public)** | Break Donchian band with ADX &gt; 20, Choppiness &lt; 40, price vs 50 Exponential Moving Average filter. Exit via ATR×3 trailing stop. |
| **Blockers** | Donchian length not explicit; no separate take-profit; ATR period for trail needs default |

### 5. `RdHzNY0K2ws` — Parabolic Stop and Reverse + EMA200 + Relative Strength Index

| field | value |
|---|---|
| **Title** | I CODED TRADING IQ's TRADING STRATEGY! HUGE PROFIT ON THE RESULTSS!!! |
| **Channel** | Aly Trading |
| **Reproducible** | MOSTLY |
| **Symbols** | BTC/USDT |
| **Timeframes** | 5-minute and/or 4-hour (both mentioned) |
| **Sides** | both |
| **Parameters** | fair defaults needed (Parabolic Stop and Reverse step/max; Relative Strength Index length) |
| **Entry / exit (public)** | Long: price above Parabolic Stop and Reverse, above EMA200, Relative Strength Index &gt; 50 (mirror short). Exit on Parabolic Stop and Reverse flip; also swing stop + 1.5 Reward:Risk stated. |
| **Blockers** | Which timeframe is authoritative for hypothesis-0 must be frozen; dual exit logic (flip vs 1.5R) needs one primary rule |

### 6. `Gzl43lj2tS4` — Dual MACD (weekly + daily), long_only

| field | value |
|---|---|
| **Title** | BITCOIN TRADING - Arguably The Best Bitcoin Trading strategy (MACD Indicator) |
| **Channel** | Financial Wisdom |
| **Reproducible** | MOSTLY |
| **Symbols** | BTC |
| **Timeframes** | Weekly + Daily |
| **Sides** | long_only |
| **Parameters** | fair defaults (standard MACD 12/26/9) |
| **Entry / exit (public)** | Enter long when weekly MACD crosses above signal **and** daily MACD crosses above signal. Exit when daily MACD crosses below signal; stop at base of daily candle wick. |
| **Blockers** | No take-profit; wick stop is bar-dependent; different family from frozen TradingRush 30m MACD |

### 7. `HmKh1hqvU5Y` — Williams Alligator stack (multi-filter)

| field | value |
|---|---|
| **Title** | ChatGPT o3: Williams Alligator Strategy for Bitcoin - WORKS ON ALL TIMEFRAMES |
| **Channel** | TradeSmart AI |
| **Reproducible** | MOSTLY |
| **Symbols** | BTC/USDT |
| **Timeframes** | many (5m–Daily); freeze one for hypothesis-0 |
| **Sides** | both |
| **Parameters** | mix — ATR stop 3.5 / take-profit 15 explicit; Alligator / ADX / Stochastic Relative Strength Index / Exponential Moving Average / Chandelier thresholds need fair defaults |
| **Entry / exit (public)** | Long: price above Exponential Moving Average, Alligator aligned green, ADX above threshold, Stochastic Relative Strength Index oversold, Chandelier filter; exit ATR take-profit / stop (mirror short). |
| **Blockers** | High rule-stack ambiguity; timeframe not unique; risk of overfit if thresholds searched |

### 8. `t6XCXDBgILQ` — Relative Strength Index + MACD + Stochastic confluence

| field | value |
|---|---|
| **Title** | RSI MACD Stochastic 99% High Accuracy Trading Strategy Tested 100 Times |
| **Channel** | Berri Kimblin |
| **Reproducible** | MOSTLY |
| **Symbols** | BTC |
| **Timeframes** | 5-minute |
| **Sides** | both |
| **Parameters** | fair defaults (standard oscillator lengths; oversold/overbought levels) |
| **Entry / exit (public)** | Long: Stochastic oversold + Relative Strength Index crosses above 50 + MACD bullish cross + volume histogram above its average (mirror short). Stop = recent swing; take-profit = 1.5× risk. |
| **Blockers** | Volume filter definition soft; 5m crypto costs/noise; hype title but rules are mechanical enough for a fixed hypothesis-0 |

---

## Near-misses (not ranked in top 8)

| video_id | why skipped / demoted |
|---|---|
| `I9WNbcrOoqI` | Reproducible **YES**, but discretionary (flags/triangles, round-number targets, “strong candle”) |
| `r55TZ-0BkoM` / `MrCWRS9npFE` | TradingRush MACD family overlap with frozen `B7jrlVeis6k` |
| `hn9o9FN8VP0` | Clean Alligator crosses on BTC; **take-profit unknown** |
| `UvS3ixWG2zs` | “Slope is Dope” long_only — slope parameters + extreme 90% stop / 60% take-profit need clarification |
| `lLFCsNP-46Y` | Alligator+ADX entries OK; exits are discretionary support/resistance |
| `gfEqy4uGe8c` | ADX+Stochastic Relative Strength Index — adjacent to frozen CoinQuant ADX family; ATR stop-finder soft |

---

## Scan notes

- Eligible true-crypto recipes with entry+exit+indicators and `YES`/`MOSTLY`: **81** (`YES`=2, `MOSTLY`=79 after exclusions).
- Prefer mechanical public indicators over discretionary Smart Money Concepts / Fibonacci / round-number recipes for hypothesis-0.
- Packaging next step: freeze one symbol + one timeframe + one exit precedence per candidate before any search.
