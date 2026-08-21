# Strategy: The Secret Mindset — Liquidity Sweep (video-faithful subset)

| Field | Value |
|-------|--------|
| **Source channel** | [The Secret Mindset](https://www.youtube.com/@TheSecretMindset) |
| **Primary video** | [ULTIMATE Liquidity Trading Strategy (Smart Money Concepts)](https://www.youtube.com/watch?v=9P7uB4nBfyA) (`9P7uB4nBfyA`) |
| **Transcript** | `C:\projects\videoanalysis\reports\secret_mindset\transcript_9P7uB4nBfyA.txt` |
| **Analysis config** | `C:\projects\videoanalysis\config_secret_mindset.yaml` |
| **Default readiness** | `LIVE_STOP / RESEARCH_ONLY` |
| **Evidence class** | `RESEARCH_PROXY` (Binance Last Open-High-Low-Close-Volume for signals; Mark for liquidation) |

## Economic rationale (from video)

Large players need opposing orders. Retail clusters stops beyond obvious swing highs/lows, equal highs/lows, session extremes, previous day/week levels, round numbers, and supply/demand or Fair Value Gap (FVG) magnets. Institutions **induce** then **sweep** that liquidity and reverse. Edge hypothesis: enter with the reverse after a confirmed stop-hunt reclaim, not on the first breakout.

## Executable rules (frozen hypothesis H0)

These are the codeable subset used for research. Non-codeable tape/order-book claims are out of scope.

### Multi-timeframe (Multi-TF)

1. Higher Timeframe (HTF) `1h` (video also mentions daily for major pools): mark swing highs/lows as liquidity.
2. Execution Timeframe (LTF) `15m`: wait for price to approach HTF liquidity, then a stop-hunt.
3. Optional micro confirmation: video mentions `5m`/`1m` for the spike — research baseline uses `15m` sweep close + next-bar entry (causal).

### Liquidity types (detection priority for H0)

| Pool | H0 implementation |
|------|-------------------|
| Structural swing high/low | Yes — swing left/right = 3 |
| Equal highs/lows | Yes — relative tolerance |
| Previous day high/low | Available in `smc.liquidity` |
| Session Asia/London/New York highs/lows | Available; session filter optional |
| Round numbers / FVG / supply-demand | Deferred to later generations |

### Entry

- **Long:** bullish sweep of sell-side liquidity (low pierces last swing low, close reclaims above it) with non-bearish HTF bias; enter on next executable bar after the closed signal bar.
- **Short:** bearish sweep of buy-side liquidity (high pierces last swing high, close rejects below it) with non-bullish HTF bias; same fill model.

### Stop-Loss (SL) / Take-Profit (TP)

- **SL:** beyond sweep extreme + small Average True Range (ATR) buffer (video: do not park stops on the obvious level).
- **TP:** opposing premium/discount or fixed Reward:Risk (default RR 2.0 for baseline; video is qualitative).

### Filters

- Prefer not chasing breakouts; H0 requires reclaim close (built into sweep definition).
- Session: baseline `none`; killzone variant registered separately before Out-Of-Sample (OOS).

## What the video said that is NOT in H0

- Order-book / market-depth / time-and-sales (no research warehouse).
- “90% of Fair Value Gaps fail” narrative (not a trade rule).
- Journaling / psychology.

## Symbols / product

Research targets: Bitcoin United States Dollar Tether (`BTCUSDT`) and Ethereum United States Dollar Tether (`ETHUSDT`) perpetual-style OHLCV. Live venue profile remains Bybit United States Dollar Tether perpetual when authorized later.

## Mapping to repo code

- Features: [`smc/`](../../smc/) + [`engine/features.py`](../../engine/features.py)
- Video-specific confluence defaults: [`confluence_config.py`](confluence_config.py)
- Signals → tradesim: [`engine/tradesim_adapter.py`](../../engine/tradesim_adapter.py)
- Runner: [`run_baseline.py`](run_baseline.py)

## Status log

- 2026-08-08: Batch-1 video transcribed; pipeline auto-extract was low quality (vision pollution). Rules documented from full transcript. Baseline research package created.
