# Strategy: Parabolic Stop and Reverse + EMA 200 + RSI (H0)

| Field | Value |
|-------|--------|
| **Source** | [`RdHzNY0K2ws`](https://www.youtube.com/watch?v=RdHzNY0K2ws) · Aly Trading (TradeIQ recipe) |
| **Readiness** | `LIVE_STOP / RESEARCH_ONLY` |
| **Evidence class** | `RESEARCH_PROXY` full-history H0 |

## Stated rules

- Bitcoin, 5-minute **and** 4-hour (video claimed 5-minute lost, 4-hour gained)
- Long: price above Parabolic Stop and Reverse, above Exponential Moving Average 200, Relative Strength Index > 50 (mirror short)
- Stop: latest swing; take-profit 1.5R; also Parabolic Stop and Reverse flip

## Fair H0 interpretation

- **4-hour only** (do not search 5-minute after the video’s own 5-minute fail)
- Parabolic Stop and Reverse 0.02 / 0.20, Exponential Moving Average 200, Relative Strength Index 14
- Rising-edge entry; swing 10; 1.5R; flip exit omitted
- Long and short **separate**
