# Research-generation freeze (practice vs exam)

Copy this file to `docs/project_memory/RESEARCH_GENERATION_FREEZE.md` (or
`artifacts/research/<id>/FREEZE.md`) and **fill every field** before any exam
Profit Factor (PF) or Sharpe is viewed. Empty exam dates = no search is allowed.

Pack source: `C:\projects\BASE CURSOR\TRADING_BOT_CURSOR_RULES_V2.zip`  
Plain language: `IN_SAMPLE_VS_OOS.md`

## Status

- **Generation id:**
- **Written (UTC):**
- **SHA-256 of this freeze file (after fill, before first exam run):**
- **Exam dates locked before any exam PF was viewed?** yes / no
- If **no**: this is **not** an exam. Label `RETROSPECTIVE_REUSED_HISTORY`. Do not call it Out-Of-Sample (OOS).

## Practice (in-sample / inner) — the only window you may tweak

- **Start (UTC, inclusive):**
- **End (UTC, exclusive):**
- **Symbols:**
- **Timeframes allowed (do not add later because the exam failed):**
- **Sides allowed:**

## Exam (out-of-sample / outer) — freeze one candidate, run once

- **Start (UTC, inclusive):**
- **End (UTC, exclusive):**
- Nested outer folds (required for `SHADOW_READY`): list fold test intervals here, all **after** their train windows.

A split such as practice 2020–2026 and exam 2027 is valid **only if 2027 was locked in this file before anyone saw 2027 PF**. If you peeked, 2027 is no longer an exam.

## Knob list (complete). Do not add rows after the exam starts

| Knob | Allowed values | Notes |
|------|----------------|-------|
| Indicator lengths | | |
| Take-profit / stop-loss | | |
| Filters | | |
| Other | | |

Search budget (max trials):  
Selection objective (inner only):  
Tie-breaker:  
Root seed:  
Gates: Frozen Version 2.1 unless a stricter profile was hashed before the exam.

## If the exam fails

Stop this generation. Report fail. Do **not** retune because the exam lost money, change timeframe, or add a filter suggested by exam losses.

A **new** written hypothesis is allowed only as a **new** freeze file. Previously viewed exam years stay `OOS_USED_FOR_SELECTION` / reused.

## Hypothesis-0 (H0) is not this form

Full-history public-recipe screens are `EXPLORATORY_IN_SAMPLE`. Do not fill this form after viewing H0 PF and then treat the same years as an exam.
