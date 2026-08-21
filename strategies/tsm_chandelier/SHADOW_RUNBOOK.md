# Shadow runbook — `tsm_chandelier` 1h

**Freeze file:** `artifacts/reports/tsm_chandelier/1h_SHADOW_FREEZE.json`  
**Max readiness:** `LIVE_STOP / SHADOW_READY` (historical only)  
**Live deploy (authorized 2026-08-10):** VPS `94.156.189.76` → `/opt/tsm-chandelier`, account **Xxobster6**, symbols BTC/ETH/SOL, min size, stop-leverage + 80% haircut, candles `SHARED_CANDLES_DB` Binance 1h via botsgeneral. Systemd: `tsm-chandelier@BTCUSDT|ETHUSDT|SOLUSDT`.

## What this bot is

- Strategy: ATR-band breakout + EMA50 filter + Chandelier stop  
- Timeframe: **1 hour**  
- Frozen primary symbols (readiness claim): **BTCUSDT**, **ETHUSDT**  
- Extra check symbol: **SOLUSDT** — exploratory replay only; **not** inside the frozen `SHADOW_READY` claim until you preregister a new multi-symbol generation

## Size (do not raise yet)

| Item | Value |
|------|--------|
| Research / shadow size | smallest exchange-legal quantity (`research_sizing`) |
| Leverage | **1×** isolated |
| Starting equity model | 10_000 USDT (wallet oversized so min-size can open) |
| Fees model | Bybit USDT perpetual non-VIP taker baseline |

Do **not** increase quantity or leverage until shadow fills match the backtest within agreed tolerances.

## Fail-closed checks (must stop / refuse new entries)

1. **Stale data** — no new closed 1h candle within expected lag → stop  
2. **Freeze hash mismatch** — running code/config ≠ `1h_SHADOW_FREEZE.json` hashes → stop  
3. **Missing instrument rules** — Bybit tick / qty step / min qty unavailable → stop  
4. **Infeasible order** — rounded size below min or exceeds risk cap → skip / stop  
5. **Duplicate process** — second runner for same strategy+symbol → stop  
6. **Unknown exchange/local state** — position/order book disagrees with local ledger → stop and reconcile  
7. **Missing protective stop** — no working stop after entry → flatten / stop  
8. **Risk limit** — margin utilisation or daily loss cap breached → stop  
9. **Conformance / engine** — tradesim stamp not green in the research path that produced the freeze → do not promote evidence

## Shadow procedure (when you authorize)

1. Confirm freeze hash on disk.  
2. Run **signal-only or paper** on Bybit testnet/mainnet shadow account — no size increase.  
3. Log every signal, intended order, fill, fee, funding, skip reason.  
4. Weekly: compare shadow trades vs re-sim on the same closed bars (parity report).  
5. Only after that parity looks good: ask for micro-live authorization separately.

## Evidence honesty

- Historical numbers used **Binance** candles + **Bybit** fee/instrument rules → class `RESEARCH_PROXY`.  
- For a venue-parity PASS later: re-sim on **Bybit-native** Open-High-Low-Close-Volume (OHLCV) + Mark price.
