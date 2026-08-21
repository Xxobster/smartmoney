# Strategy: The Secret Mindset — Triple EMA Pullback Continuation

| Field | Value |
|-------|--------|
| **Source** | [Moving Average Trading Strategy EXPOSED (The 3-EMA Trading Strategy)](https://www.youtube.com/watch?v=kuzYxzSxEAg) (`kuzYxzSxEAg`) |
| **Transcript** | `C:\projects\videoanalysis\reports\secret_mindset\transcript_kuzYxzSxEAg.txt` |
| **Readiness** | `LIVE_STOP / RESEARCH_ONLY` |
| **Evidence class** | `RESEARCH_PROXY` |

## Economic rationale

Exponential Moving Averages (EMAs) 20 / 100 / 200 describe alignment and space. In a valid trend, shallow pullbacks to the medium EMA often resume; the video explicitly rejects EMA **crossovers** as entries.

## Executable H0

### Indicators
- EMA20, EMA100, EMA200 (exponential, close)

### Trend alignment
- **Bull:** close > EMA20 > EMA100 > EMA200 and EMA100 slope up (EMA100 > EMA100[n-3])
- **Bear:** close < EMA20 < EMA100 < EMA200 and EMA100 slope down

### Entry (continuation only)
- **Long:** bull alignment; bar touches/crosses into EMA100 from above (low ≤ EMA100 ≤ high) and closes back above EMA100 (rejection/bounce proxy). Prefer EMA100–EMA200 space not contracting vs 5 bars ago.
- **Short:** mirror.

### Exit
- Stop beyond pullback extreme (bar low/high) with small buffer  
- Take-Profit Reward:Risk **2.0**  
- Max hold 64 bars on **15m** (also test **1h** — video is TF-agnostic)

### Explicitly NOT H0
- Crossover entries  
- Range / reversal setups (documented for later families)

## Symbols
Bitcoin / Ethereum United States Dollar Tether (`BTCUSDT`, `ETHUSDT`)
