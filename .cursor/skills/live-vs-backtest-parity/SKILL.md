---
name: live-vs-backtest-parity
description: >-
  Compare smartmoney VPS live bots vs local backtests (candles, indicators,
  signals, exits). Use when the user asks for live parity, live vs backtest,
  reconcile live trades, or says “live parity” / “run live parity”.
---

# Live vs backtest parity (this project only)

Scope: **bots deployed from this `smartmoney` repo** (currently `tsm_chandelier` on VPS `94.156.189.76` / `ln1` / `eventactivities-vps`). Do **not** include llm2, xgb, crypthor, or other repos.

## User workflow (verbatim)

Only for the bots from this project:
Compare live trades vs backtests. First fetch latest candles locally for all the pairs on the VPS (also 1min for precise entries/exits). Then compare live data vs backtest data :
candles
all calculations (indicators, etc...)
signals
exists
strategy specificities
Check if the strategy is working as it is supposed to (basically every strategy on the vps have profitable backtests).
If there are differences between live and backtest (we assume that there could be entry/exit small differences due to slippage), create a report, find a solution and fix it, unless it makes fundamental changes to the strategy that risk to make more damage.

## How to run (preferred)

From the repo root, one command:

```bash
python scripts/live_parity.py
```

Options:

```bash
python scripts/live_parity.py --skip-fetch    # reuse local candles / live DB already pulled
python scripts/live_parity.py --plot         # also open finplot live vs BT overlay
python scripts/live_parity.py --host ln1     # SSH host alias (default eventactivities-vps)
```

This orchestrates: pull live SQLite from VPS → refresh local Binance 1h + 1m → run `research/compare_live_vs_bt_full_vps94.py` → print readiness / blockers / report paths.

## Agent checklist

1. Read `docs/project_memory/CURRENT_STATE.md` and trading-bot core rules.
2. Run `python scripts/live_parity.py` (do not only describe it).
3. Lead the reply with: maximum earned readiness, evidence class, principal blocker.
4. Compare explicitly: candles, indicators/signal core, signals, entries/exits, strategy params (ATR band, chandelier, EMA filter, max hold, min size).
5. **Acceptable by design:** Bybit market fill vs Binance next-open + entry slip; live Stop Loss market slip vs backtest planned-stop / zero exit slip; funding gaps; cross vs isolated margin.
6. **Material bugs (fix):** wrong signal side/bar; stop/target mismatch beyond tick; exit reason disagrees with 1m path; research `signals.py` ≠ live `signals_core.py`; VPS deploy code ≠ local deploy; missing/stale candles causing wrong entries.
7. If material: write/update report under `artifacts/reports/tsm_chandelier/`, implement the smallest safe fix, add a regression test, re-run parity until green or blocked on user authority.
8. Do **not** change TP/SL/leverage/size/filters to “make live look better.” Do **not** deploy/restart live without explicit user authorization for that action.
9. Update `docs/project_memory/CURRENT_STATE.md` after a meaningful parity run.

## Reports

- Full JSON: `artifacts/reports/tsm_chandelier/live_vs_bt_full_*.json`
- Sitrep markdown when present: `artifacts/reports/tsm_chandelier/live_vs_bt_full_*.md`
- CLI also prints paths at the end.

## Related scripts

- `research/refresh_research_ohlcv_from_binance.py` — local 1h + 1m refresh
- `research/compare_live_vs_bt_full_vps94.py` — comparison engine
- `research/plot_live_vs_backtest_finplot.py` — cyan live / orange backtest chart
- `research/reconcile_live_closed_vps94.py` — closed-trade fee/funding deep dive
