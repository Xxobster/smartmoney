# Strategy: Monday range sweep, trigger 1 (H0)

| Field | Value |
|-------|--------|
| **Source** | [`BFdEPlNSaps`](https://www.youtube.com/watch?v=BFdEPlNSaps) · Trader Mine Monday range (YouTube recap) |
| **Captions** | Official YouTube automatic English captions (`youtube_auto`) |
| **Readiness** | `LIVE_STOP / RESEARCH_ONLY` |
| **Evidence class** | `RESEARCH_PROXY` |

Creator claims are **not** evidence. Discord/PDF extras are ignored. Trigger 2 (Monday-open sweep + Inner Circle Trader premium/discount) is **not** in this H0.

## Stated rules (trigger 1)

- Symbols: Bitcoin / Ethereum
- Execution timeframe: **1 hour**
- Bias: daily **SuperTrend**
- Monday range: high / low from **midnight Sunday to midnight Monday**, New York time (Eastern)
- After the Monday range has printed: wait for a **1-hour close outside** the range (wick-only does not count), then a **1-hour close back inside**
- Enter on that close-back-inside (we use **next open**)
- Stop: recent swing / sweep extreme
- Target: **opposite side** of the Monday range
- Break-even at range midpoint (stated; **not coded** — skipping it is more conservative)
- Skip **Friday and Saturday**; want at least **2R**

## Our interpretation (not attributed to the creator)

- Monday window = New York **Monday 00:00 to Tuesday 00:00** (crypto 24/7 Monday session)
- SuperTrend = default **Average True Range 10, multiplier 3** on **completed** daily bars
- Stop = high/low of the close-back-inside bar
- Skip the week if reward / risk at the signal close is **< 2**
- One new signal per week per side

## Result

**FROZEN.** Full-history hypothesis-0 failed (Bitcoin Profit Factor 0.38; Ethereum 0.85). Do not search SuperTrend length, session clock, or 2R on that result. Do not unfreeze MACD, Bollinger, or the Algovibes Ethereum dip.
