# Strategy: Donchian + Average Directional Index + Choppiness (H0)

| Field | Value |
|-------|--------|
| **Source** | [`CgYdfwrL1VQ`](https://www.youtube.com/watch?v=CgYdfwrL1VQ) · Quant Tactics |
| **Readiness** | `LIVE_STOP / RESEARCH_ONLY` |
| **Evidence class** | `RESEARCH_PROXY` full-history H0 |

## Stated rules

- Ethereum perpetual, 1-hour
- Break Donchian band, Average Directional Index (ADX) > 20, Choppiness < 40, price vs 50 Exponential Moving Average (EMA)
- Exit: Average True Range (ATR) × 3 trailing stop

## Fair H0 interpretation

- Donchian length **20** (not stated)
- ADX 14, Choppiness 14, EMA 50, ATR 14 × 3 **initial** stop (trail omitted)
- Prior-bar Donchian (shift-1) so the signal close is not inside its own channel
- Long and short reported **separately** — never pooled
