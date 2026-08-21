# Smart Money Concepts (SMC) LLM Strategy Finder

Offline research system that turns the SMC course knowledge base into
economically justified strategy hypotheses, then validates them with a
deterministic nested walk-forward engine against frozen Trading-Bot V2.1 gates.

## Guiding principle

The Large Language Model (LLM) is a **hypothesis generator**, never a
winner-picker. Selection and validation use nested walk-forward with
purge/embargo. The LLM never sees out-of-sample folds. Every trial is logged
append-only. Scores are deflated for multiple testing.

A **negative result** (no edge found) is a valid successful research outcome.

## Layout

- `config/` — project profile, frozen gates, preregistered search space
- `docs/project_memory/` — V2 research standard, gates, project profile
- `data/` — instrument specs, funding download, dataset split builder
- `smc/` — vectorized SMC primitives (structure, liquidity, OB, FVG, PD, volume)
- `engine/` — features, backtest, metrics, walk-forward, parity tests
- `llm/` — local open-source model zoo, Retrieval-Augmented Generation (RAG), proposer
- `research/` — search orchestrator, OOS eval, registry, report
- `tests/` — unit and causality tests
- `artifacts/` — datasets, trial registry, reports (generated)

## Data

Primary candles: `D:/projectsdata/candles/market_ohlcv.sqlite`

SMC knowledge: `C:/projects/wavetheory/smart_money_concepts`

## Quick start

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt

# 1) Build research + forward lockbox SQLite files
python -m data.build_datasets

# 2) Download funding history (optional; falls back to no-funding label)
python -m data.download_funding

# 3) Build RAG index over SMC docs
python -m llm.rag --build

# 4) Run inner search (logical seed + LLM proposals + Optuna)
# Default: fast heuristic proposer grounded in SMC RAG.
# Optional heavy local LLMs: set SMARTMONEY_LOAD_LLM=1
python -m research.run_search

# 5) Freeze one candidate and evaluate ONCE on outer OOS
python -m research.run_oos

# 6) Report readiness
python -m research.report
```

## LLM models (downloaded from the internet)

**Preferred path (this machine):** [Ollama](https://ollama.com) — already installed.

```powershell
# Ensure a small instruct model is present (one-time)
python -m llm.model_zoo

# Use real LLM proposals in search
$env:SMARTMONEY_LOAD_LLM="1"
$env:SMARTMONEY_RAG_LIGHT="1"   # recommended on Windows CPU (avoids BGE reload crashes)
python -m research.run_search --max-proposals 3 --optuna-trials 3 --symbols BTCUSDT
```

- Default Ollama tag: `qwen2.5:1.5b-instruct` (pulled locally; fast on CPU).
- Also usable if present: `qwen2.5:14b-instruct`, `qwen2.5vl:7b`.
- Hugging Face `transformers` is a **fallback only** if Ollama is down, with a hard load timeout (default 180s) and truncated prompts — this avoids the previous CPU hang.
- Heuristic proposer remains the last resort when no LLM backend loads.

Timeouts (optional env):
- `SMARTMONEY_LLM_LOAD_TIMEOUT` (default 180)
- `SMARTMONEY_LLM_GEN_TIMEOUT` (default 120)
- `SMARTMONEY_USE_OLLAMA=0` to disable Ollama

## Readiness

Historical research alone may earn at most `SHADOW_READY`. Live deployment
requires separate explicit user authorization.

Default state: `LIVE_STOP / RESEARCH_ONLY`.
