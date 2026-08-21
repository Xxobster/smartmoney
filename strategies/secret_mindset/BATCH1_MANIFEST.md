# Batch 1 manifest — The Secret Mindset

**Status:** pipeline running  
**Config:** `C:\projects\videoanalysis\config_secret_mindset.yaml`  
**Command:**

```text
python main.py --config config_secret_mindset.yaml --urls data/secret_mindset/batch1_urls.txt --max-videos 8
```

## Selection method

1. Flat-list inventory of `@TheSecretMindset` (267 videos) via `yt-dlp`
2. Trading-relevance score (`scripts/inventory_secret_mindset.py`) — prefers strategy/setup/indicator titles; downranks psychology/vlog/prediction
3. First 8 unique rule-families from the ranked list

## After analysis

For each distinct executable rule set that survives consolidation:

1. Create `strategies/<slug>/` under this repo
2. Document rules in `STRATEGY.md` (entries, exits, filters, timeframes, symbols)
3. Implement feature builder + `Signal` emitter for `botsgeneral` tradesim
4. Run leakage audit (`prefer_botsgeneral_leakage`) before any search
5. Backtest Bitcoin United States Dollar Tether (BTCUSDT) and Ethereum United States Dollar Tether (ETHUSDT) on the strategy’s stated timeframes
6. Lead results with maximum earned readiness (default `LIVE_STOP / RESEARCH_ONLY`)
