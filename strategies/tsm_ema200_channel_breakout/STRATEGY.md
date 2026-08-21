# Strategy: The Secret Mindset — 200 EMA Channel Confluence Breakout

| Field | Value |
|-------|--------|
| **Source** | [The 200 EMA Confluence Trading Strategy](https://www.youtube.com/watch?v=imp63ZnLyck) (`imp63ZnLyck`) |
| **Transcript / JSON** | `C:\projects\videoanalysis\reports\secret_mindset\transcript_imp63ZnLyck.txt`, `video_imp63ZnLyck_strategy.json` |
| **Readiness** | `LIVE_STOP / RESEARCH_ONLY` |
| **Evidence class** | `RESEARCH_PROXY` |

## Economic rationale

A dual 200 Exponential Moving Average (EMA) channel (high-sourced and low-sourced) defines a confidence band. Breaks with retest plus structure/Fibonacci confluence aim to catch continuation after trapped counter-trend traders.

## Executable H0 (simplified)

Discretionary chart patterns (H&S, double top) are **out** of H0. Codeable core:

1. `ema200_high` = EMA(200) of highs; `ema200_low` = EMA(200) of lows  
2. **Long:** close crosses above `ema200_high` after being below; within next 12 bars, pullback touches band (`low <= ema200_high`) and closes back above; enter next bar.  
3. **Short:** mirror vs `ema200_low`.  
4. Stop beyond channel extreme; Take-Profit Reward:Risk **3.0** (video minimum).  
5. Timeframes: **15m** and **5m** mentioned — research baseline **15m** (+ **1h** sensitivity).

## Symbols
`BTCUSDT`, `ETHUSDT`
