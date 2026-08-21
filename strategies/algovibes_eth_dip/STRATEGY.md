# Strategy: Algovibes Ethereum hourly dip (H0)

| Field | Value |
|-------|--------|
| **Source** | [`pWm4fFsJXt4`](https://www.youtube.com/watch?v=pWm4fFsJXt4) · Algovibes (`UC87aeHqMrlR6ED0w2SVi5nw`) |
| **Captions** | Official YouTube automatic English captions (`youtube_auto`) |
| **Readiness** | `LIVE_STOP / RESEARCH_ONLY` |
| **Evidence class** | `RESEARCH_PROXY` |

Creator claims are **not** evidence. Default assumption: unproven until independent Out-Of-Sample (OOS).

## Stated rules (from captions / coded example)

- Market: Ethereum versus Tether (`ETHUSDT`), also transferable to Bitcoin Tether (`BTCUSDT`)
- Timeframe: **1 hour** (creator says 4 hour / daily also possible)
- Long only
- Buy when hourly close-to-close return **≤ −1%**
- Fill: **next candle open** (stated)
- Exit if a later hourly return **≥ +0.5%** (rise threshold) **or** **5 hours** max hold
- Creator mentions Binance fee **0.15%** round-trip as an example; we use the project Bybit-style cost model instead
- No Stop-Loss in the simple script (creator said you can add one)

## Our interpretation (not attributed to the creator)

- Protective stop **3%** so the engine has a hard invalidation (video had none)
- Take-Profit price **+0.5% from entry** as a mechanical stand-in for “sell on a +0.5% hour”
- Test **1h** primary and **4h** as a transfer check
- Symbols: `ETHUSDT`, `BTCUSDT`

## Availability

`FREE_STANDARD` — Open-High-Low-Close-Volume only. Course pitch in the description is `PAID_OPTIONAL` and not required.
