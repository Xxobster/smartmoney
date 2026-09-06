# Strategy: Turtle Donchian System 1 (H0)

| Field | Value |
|-------|--------|
| **Source** | [`dk9c7jC3VO4`](https://www.youtube.com/watch?v=dk9c7jC3VO4) · Ssmurf gg |
| **Readiness** | `LIVE_STOP / RESEARCH_ONLY` |
| **Evidence class** | `RESEARCH_PROXY` |

## Public rules used

- Daily Donchian System 1: break prior **20**-day high/low
- Stop: **2 × Average True Range (20)** from signal close
- Long and short both exist; reported separately

## Explicitly omitted in this H0

- Pyramiding (0.5 Average True Range adds, max 4 units)
- System 1 “skip if last trade loser” filter
- 10-day channel exit (safety max_hold only)
- System 2 (55 / 20)

Freeze on fail. Do not add pyramiding to rescue a weak baseline.
