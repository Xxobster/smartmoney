# AUTO agent brief — Smart Money Concepts (SMC) strategy finder

Copy/paste this brief into a Cursor AUTO agent session to continue or rebuild.

## Objective

Build and run an offline Python research system that:

1. Turns the SMC knowledge base at `C:/projects/wavetheory/smart_money_concepts` into
   economically justified `StrategySpec` hypotheses using **local open-source LLMs**
   downloaded from the internet (Hugging Face / llama.cpp).
2. Validates candidates with a **deterministic nested walk-forward** engine against
   frozen V2.1 gates.
3. Produces an honest readiness sitrep. A negative result is a valid success.

## Non-negotiables (from Trading-Bot Cursor Rules V2.1)

- Read `docs/project_memory/TRADING_BOT_RESEARCH_STANDARD_V2.md`,
  `docs/project_memory/FROZEN_DEFAULT_GATES_V2_1.md`,
  `docs/project_memory/TRADING_PROJECT_PROFILE.md` before claiming readiness.
- LLM is a **hypothesis generator**, never a winner-picker. Never select on outer OOS.
- Two physical SQLite files: research + forward lockbox. Features computed **separately**.
- Append-only trial registry. Deflated Sharpe Ratio accounts for all trials.
- Default state: `LIVE_STOP / RESEARCH_ONLY`. Do not deploy, restart VPS, or place orders
  without explicit user authorization for that exact action.
- Vectorize indicators/features (NumPy/pandas). Event loop only for path-dependent fills.
- Auto-debug until tests are green after each phase.

## Phase order

1. Scaffold + configs (done if repo exists).
2. `python -m data.instrument_specs` and `python -m data.download_funding`.
3. `python -m data.build_datasets` → research + lockbox DBs under `artifacts/datasets/`.
4. SMC primitives + `pytest tests/`.
5. Features / backtest / metrics / walk-forward.
6. LLM stack: `python -m llm.rag --build` then proposer (heuristic fallback OK if download fails).
7. `python -m research.run_search` (logical seed first, then LLM proposals + Optuna).
8. `python -m research.run_oos` (evaluate frozen candidate **once**).
9. `python -m research.report` → sitrep.

## Data

- Candles: `D:/projectsdata/candles/market_ohlcv.sqlite`
- Primary symbols: BTCUSDT, ETHUSDT
- Target: Binance USDT-M linear perpetual (spot proxy label if funding missing)

## Success criteria

- Tests green.
- Trial registry populated (including failures).
- Sitrep states maximum earned readiness, evidence class, principal blocker.
- Forward lockbox untouched until after freeze (lockbox eval is optional last step and
  must not retune).

## Forbidden

- Expanding the search space after viewing OOS because nothing passed.
- Using full-history backtests as deployment evidence.
- Silent OHLC fills, lookahead HTF joins, or selecting winners on outer folds.
