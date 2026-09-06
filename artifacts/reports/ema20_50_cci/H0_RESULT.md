# 20/50 Exponential Moving Average + 200 EMA + CCI — hypothesis-0

| Field | Value |
|-------|--------|
| **Maximum earned readiness** | `LIVE_STOP / RESEARCH_ONLY` |
| **Evidence class** | `EXPLORATORY_IN_SAMPLE` (full-history Hypothesis-0, not a 2027-style exam). Data: `RESEARCH_PROXY` (engine stamp NOT GREEN) |
| **Principal blocker** | Frozen Version 2.1 gates fail: Profit Factor (PF) 0.62–0.92; Sharpe negative on every 1-hour leg |
| **Live-test candidate?** | **No** |

Source: `RFMM8WkLXVI` (Crypto Trading; stated 30-minute Bitcoin). Mapped to 1-hour. Leakage: **PASS** (`LEAKAGE_POTENTIAL=0`).

Fair freeze: EMA 20 cross EMA 50; both vs EMA 200; Commodity Channel Index (CCI) 14 above +100 / below −100; stop 1 × Average True Range (ATR) 14; take-profit 1.5R. Session hours omitted.

Period: 2020-01-01 → 2026-08-25.

| Symbol | Side | Trades | Trades/mo | PF | Sharpe (ann.) | HAC Sharpe | Win rate | Net PnL |
|--------|------|--------|-----------|-----|---------------|------------|----------|---------|
| BTCUSDT 1h | long | 113 | 1.42 | 0.77 | −0.42 | −0.37 | 47.8% | −6.1 |
| BTCUSDT 1h | short | 115 | 1.44 | 0.62 | −0.78 | −0.78 | 37.4% | −12.0 |
| ETHUSDT 1h | long | 106 | 1.33 | 0.76 | −0.48 | −0.47 | 43.4% | −4.2 |
| ETHUSDT 1h | short | 100 | 1.25 | 0.92 | −0.13 | −0.14 | 43.0% | −1.2 |

This is **not** a retune of the frozen Commodity Channel Index zero-line pack (CCI is a filter on an EMA cross, not the trigger). Do not search 20/50/200, CCI 100, or ATR after viewing these numbers.

**FROZEN.** Not a live or shadow candidate.
