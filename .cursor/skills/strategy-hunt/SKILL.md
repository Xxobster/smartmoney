---
name: strategy-hunt
description: >-
  Hunt or package a trading strategy, run Hypothesis-0 (H0), search Tenkan /
  take-profit / stop-loss / timeframe, walk-forward, or look for a profitable
  edge. Forces practice vs exam: freeze years and knobs before exam Profit
  Factor (PF). Use when the user says hunt, H0, find an edge, optimize, or
  backtest a YouTube recipe.
---

# Strategy hunt (practice vs exam)

**Pack:** `C:\projects\BASE CURSOR\TRADING_BOT_CURSOR_RULES_V2.zip`  
**Must read:** `docs/project_memory/IN_SAMPLE_VS_OOS.md` and `docs/project_memory/TP_SL_MAKER.md`  
**Hashes (detect old pack):** `docs/project_memory/INSTALLED_STANDARD_HASHES.md`  
**Before a real search:** fill `docs/project_memory/RESEARCH_GENERATION_FREEZE.template.md` into `RESEARCH_GENERATION_FREEZE.md`

## Rules (do not skip)

1. Run `python scripts/hash_installed_standard.py` if hashes are missing or `vs_pack` is `DIFFERS_FROM_PACK`. Re-copy the zip if this repo is behind.
2. **Hypothesis-0 (H0)** full-history public-recipe screens are `EXPLORATORY_IN_SAMPLE`. They are **not** a 2027-style exam. After viewing H0 Profit Factor (PF), do not hunt nearby knobs on the same symbols and years.
3. A **real search** (Tenkan, take-profit, stop-loss, timeframe, side) requires the freeze file **before** any exam PF: practice years, exam years, complete knob list. Example “2020–2026 fit, 2027 test” is valid **only if 2027 was locked before anyone saw 2027 PF**. If you peeked, it is no longer an exam.
4. If the exam fails: **stop that generation**. A new written hypothesis is allowed. Retuning because 2027 lost is not.
5. Headline = stitched outer Out-Of-Sample (OOS), not the best in-sample PF. Index: `docs/project_memory/H0_TEST_REGISTRY.md`.
