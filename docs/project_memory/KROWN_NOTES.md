# Krown channel notes (public analysis, not paid reverse-engineering)

Channel: [Krown](https://www.youtube.com/@Krown) · `UCnwxzpFzZNtLH8NgTeAROFA`. Former New York Stock Exchange (NYSE) ARCA market-maker framing. Most recent ~80 videos are **narrative technical analysis**, **seasonality stories**, and **macro**, not copy-paste recipes. Paid products (Krown Trading Bible, HPDR bands/cones/oscillator, HPAS, Advanced Stochastic + Directional Movement Index (DMI) “reverse function”, Caretaker Relative Strength Index (CT RSI)) are **not** reverse-engineered here.

Maximum earned readiness on every public recipe we actually backtested: `LIVE_STOP / RESEARCH_ONLY`. **No live-test candidate.**

## Public mechanical recipes we tested

| Video | Recipe | Our pack | Verdict |
|-------|--------|----------|---------|
| `C0wM-iKfwaI` | Daily close above 5 Exponential Moving Average (EMA) → long; close below → exit. Claimed Profit Factor (PF) ~2.72 since 2013, win rate ~31.6%, no hard stop | `krown_ema5_daily` | H0 + pre-registered paper-cut H0b both fail Frozen Version 2.1. **FROZEN** |
| `hTcz81O2w-o` | 1-hour Relative Strength Index (RSI) 14 fresh cross above 70 + close above 200 Simple Moving Average (SMA) + 4-hour RSI > 50 + daily RSI > 50; exit 24 hours later | `krown_rsi_momentum_burst` | Best leg Ethereum long PF 1.26, Sharpe 0.53. Shorts lose. **FROZEN** — do not copy the 576-variant search |

Do **not** copy on-video parameter clicks (Friday-skip on the 5 EMA) or the 576 / 1,600 / 888 “I backtested N versions” winners. Those are selection on inspected history.

## Theories and indicator notes (from captions)

### Technical analysis order (`hNfjyrJEytI`)

Four layers, most → least important:

1. **Trend** (direction). Higher timeframe dominates lower. Eyes first; moving averages optional (examples he named: 5 vs 21 Exponential Moving Average (EMA), 21/50/55, 50 and 200). If the trend is not obvious, wait.
2. **Volatility** (when a move is likely). Free TradingView **Bollinger Band Width Percentile (BBWP)** by Caretaker. Settings he likes on Bitcoin higher timeframes: basis length **7**, lookback **100**, Simple Moving Average (SMA), plus a **5**-period SMA on the percentile. High ≈ above **85th** percentile; low ≈ below **25th**. Volatility is **not** direction. Low-vol (squeeze) precedes expansion; do not fade trend-trade inside the squeeze.
3. **Structure** (how a range/high-low set is evolving: break vs hold).
4. **Momentum** last (Relative Strength Index (RSI) / divergences). Must be read **inside** trend + vol + structure. His preferred divergence oscillator is **paid** Caretaker RSI — skip.

### Relative Strength Index (RSI) reading (`INOCBmqQupc`)

- RSI measures **push / strength**, not a buy/sell button. Trend decides direction.
- “Overbought” ≈ RSI **> 70** is **strong momentum**, not an automatic sell. Strong uptrends **stay** overbought; selling there is how you exit winners. Same for oversold in downtrends.
- Regime zones (his teaching, not a frozen H0): uptrend RSI often holds **40–80** (pullback lows near 40–50); downtrend **20–60**; chop often **40–60** (textbook 30–70). Mid-zone → do not run a trend strategy.
- Markets can stay overbought **longer** than they stay deeply oversold.
- Divergences (standard teaching): regular bullish = price lower low, RSI higher low (exhaustion); hidden bullish = price higher low, RSI lower low (continuation). Regular/hidden bearish are the mirrors. Use as confirmation, not a standalone trigger.

### Momentum-burst search he already ran (`hTcz81O2w-o`)

He states the four-rule + 24-hour time exit **first**, then searches 576 exits/filters. His own on-video ablations: exit when RSI loses its 5-period average **failed**; exit when RSI back below 70 **lost money**; dropping the daily RSI > 50 filter still “profitable” overall but **bled 2025**. 270 of 576 variants made nothing. We tested only the **pre-search public four rules**. We will not pick a 576 winner after seeing our numbers.

### Volatility entry (`kcMnnQr1VFg`)

BBWP squeeze → expansion cycle. High BBWP ≈ violent pumps/dumps; low BBWP ≈ boring ranges that last longer than the violent legs. **Not a complete long/short recipe** (no direction rule). Pair with trend (layer 1). Do not invent a BBWP-direction grid after looking at results.

### Daily 200 Simple Moving Average (SMA) (`_92fXlj7WyU`)

Narrative: Bitcoin rejected daily 200 SMA; he still leaned **higher-timeframe hidden bullish** rather than “rejection = short.” Not a mechanical entry/exit. Do not freeze a “fade the 200 SMA” H0 from this tape.

### Seasonality / calendar (titles, not recipes)

Recent titles claim: “worst month” September is a **myth**; every red September did X first (9/9); August closed red 8 of last 11; April disaster 5 years straight. These are **story filters**. Do not add calendar gates to a failed pack after viewing full history.

### Other on-camera searches to ignore

- `5NCnVr7NzqU` — 1,600 ways to buy a Bitcoin dip (almost all lose).
- `IE8-Ds-IC2o` — 888 versions of a “+25% in 90 days” signal.

### Candlesticks (`8MvxK_nxO-0`)

Title: only four patterns beginners need. Not extracted as an H0 (beginner pattern tape, not a full executable recipe).

## Paid / not replicable

- Caretaker RSI (divergence tool; he said not free).
- Historical mentions of HPDR bands/cones/oscillator, HPAS, Advanced Stochastic + Directional Movement Index (DMI) reverse. Do not reconstruct scripts.

## Honest “improve if unsuccessful” policy

Allowed: reverse long/short as a **separate** pre-registered leg; **one** improvement taken from the source’s own words and frozen **before** looking at our Profit Factor (PF).

- 5 EMA: paper-cut `|close−EMA| > 0.25 × Average True Range (ATR) 14` was that improvement. It helped a little (Bitcoin long PF 1.47 vs 1.33) and still failed Sharpe. **Stop.**
- Momentum burst: his own words say extra exits **hurt**. No second improvement after viewing our full-history numbers.
