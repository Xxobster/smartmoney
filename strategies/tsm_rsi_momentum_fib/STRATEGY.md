# Strategy: The Secret Mindset — RSI Momentum + Fibonacci Pullback

| Field | Value |
|-------|--------|
| **Source** | [I Regret Not Using This RSI Day Trading Strategy Before](https://www.youtube.com/watch?v=Se1UJPhGnLQ) (`Se1UJPhGnLQ`) |
| **Transcript** | `C:\projects\videoanalysis\reports\secret_mindset\transcript_Se1UJPhGnLQ.txt` |
| **Readiness** | `LIVE_STOP / RESEARCH_ONLY` |
| **Evidence class** | `RESEARCH_PROXY` |

## Economic rationale

Classic “fade overbought/oversold” is crowded. Video hypothesis: Relative Strength Index (RSI) ≥70 / ≤30 marks **momentum continuation**. Wait for a shallow Fibonacci retracement that traps mean-reversion traders, then enter with the trend on rejection.

## Executable H0 (frozen before Out-Of-Sample)

### Indicators
- RSI length **14** (Wilder), thresholds **70 / 30**
- Optional filter: 50-period Exponential Moving Average (EMA) — long only if close > EMA50; short only if close < EMA50 (**ON** in H0)
- Fibonacci levels on the impulse leg: **23.6%, 38.2%, 50%**

### Timeframes / symbols
- Execution: **15m** (video also allows 30m)
- Symbols: Bitcoin United States Dollar Tether (`BTCUSDT`), Ethereum United States Dollar Tether (`ETHUSDT`)

### Long
1. RSI crosses **above 70** (signal armed on that closed bar).
2. Wait for a pullback that touches any of Fib 23.6 / 38.2 / 50 of the impulse from swing-low → swing-high enclosing the arming move (causal swings).
3. Enter next bar after a **rejection close** back above the touched Fib (proxy for engulfing/pinbar).
4. Stop below pullback low (or below 50% Fib if tighter); target Reward:Risk **2.0**.

### Short
Mirror: RSI cross below 30 → Fib on swing-high → swing-low → rejection close below Fib → RR 2.0.

### Out of scope for H0
Discretionary “further confirmation”, variable RR 1.5–3, stochastic/CCI substitutes.

## Package layout
- `build_features.py` — leakage builder  
- `signals.py` — vectorized arm → pullback → rejection  
- `run_baseline.py` — tradesim RESEARCH_PROXY baseline  
- `run_leakage.py` — botsgeneral leakage audit  
