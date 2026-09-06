# In-sample search vs out-of-sample proof

**Status:** truth constraint (not a gate you may relax after seeing numbers)  
**Read this before any parameter hunt, take-profit / stop-loss search, or “try another timeframe.”**  
**Canonical detail:** `TRADING_BOT_RESEARCH_STANDARD_V2.md` sections 0.5, 15, 16.

Using history is **required**. Reporting the **same** years you used to pick Tenkan, Kijun, take-profit, stop-loss, side, or timeframe as **proof** is **forbidden**.

---

## 1. Two jobs for historical candles

| Job | Also called | What the agent MAY do | What the number means |
|-----|-------------|------------------------|------------------------|
| **Practice** | In-sample (IS), inner window, `outer_train` | Tweak indicator lengths, take-profit, stop-loss, filters, side, timeframe — **only inside this window**, from a list written **before** the exam is viewed | “This setting **fit** that stretch of history.” |
| **Exam** | Out-of-sample (OOS), outer test, lockbox | Run **one** frozen setting **once**. No more tweaks. | “It still worked on candles the search was **not** allowed to use.” |

Walk-forward **is** “tweak the past, then test later past.” It does **not** mean: tweak until 2020–2026 Profit Factor (PF) looks good, then quote that same 2020–2026 Profit Factor (PF).

**Agreed operator rule:** if the strategy is profitable on the practice years and **not** profitable on the exam years, the strategy is **not working**. Do not keep shopping settings until the exam also looks good. That turns the exam back into practice.

---

## 2. Simple picture (must not be violated)

Allowed:

- Search Tenkan / Kijun / take-profit / stop-loss on **2020–2026** (if that window was registered as practice).
- Freeze **one** winner.
- Test **once** on **2027** (or the next outer fold), which the search never saw.
- Headline = the exam (stitched outer Out-Of-Sample), not the practice Profit Factor (PF).

Forbidden:

- Search on 2020–2026, then report 2020–2026 Profit Factor (PF) as the edge.
- Fail the 2027 exam, then try 1-hour, weekly, or a fatter cloud **because** 2027 failed. The choice of the next test used the exam score. Label that history `OOS_USED_FOR_SELECTION` / `RETROSPECTIVE_REUSED_HISTORY`. Start a **new** hashed generation; do not call it clean Out-Of-Sample (OOS).
- Rank many candidates on the exam and keep the winner. The exam became a leaderboard.

A ratio such as “six years practice, one year exam” is only valid if the exam year was **not** used to choose parameters, symbols, side, or timeframe. Frozen Version 2.1 `SHADOW_READY` still needs **nested** walk-forward (several outer folds), not a single pretty split after looking at the chart.

---

## 3. This is not feature leakage

| Mistake | Who peeked | Typical example |
|---------|------------|-----------------|
| **Code leakage** | The program | Tenkan uses tomorrow’s high; a library `centered=True` window |
| **Search on inspected data** | The researcher / agent | Causal 9/26/52 backtest already printed; then try Tenkan 7, 1-hour, weekly until Profit Factor (PF) looks good |

Train/test SQLite files and a leakage audit **do not** fix researcher look-ahead. Both checks are required.

---

## 4. What counts as a “tweak” (every one is a trial)

Record each attempt. Do not reset the trial log between scripts or chats.

- Indicator lengths (Tenkan, Kijun, moving averages, …)
- Take-profit, stop-loss, break-even, trail, max hold
- Timeframe, symbol, long vs short
- Extra filters (cloud thickness, higher-timeframe bias) added **after** seeing a score
- Dropping a losing year or a losing coin after seeing Out-Of-Sample (OOS)

Take-profit / stop-loss search **inside practice** is allowed. Using exits to maximize Profit Factor (PF) on the **exam** is not finding a better entry; it is fitting that path.

---

## 5. Full-history Hypothesis-0 (H0)

A first freeze of a **public** recipe on all available bars is `EXPLORATORY_IN_SAMPLE` (or a one-shot public-recipe screen). It is **not** a 2027-style exam. It is **not** nested outer Out-Of-Sample (OOS) and **cannot** earn `SHADOW_READY`.

After that report is viewed, **do not** hunt nearby knobs on the same symbols and years. That is searching on inspected data. A new generation needs a new written hypothesis and must label those years reused.

Fill `RESEARCH_GENERATION_FREEZE.template.md` **before** any real search. Empty freeze = no search.

---

## 6. Agent MUST / MUST NOT

**MUST**

- Write practice years, exam years, and the **full knob list** in the freeze file **before** viewing outer Out-Of-Sample (OOS) Profit Factor (PF) or Sharpe.
- Lock exam dates before the first exam PF. A split such as 2020–2026 fit / 2027 test is valid **only if 2027 was locked before anyone saw 2027 PF**. If you peeked, it is no longer an exam.
- Select only inside inner / practice windows.
- Evaluate exactly one frozen choice **once** per outer exam.
- Lead the user-facing result with stitched outer Out-Of-Sample (OOS), evidence class, and blockers — **not** the best in-sample Profit Factor (PF).
- If practice looks good and the exam does not: report **fail**, **stop that generation**. A new written hypothesis is allowed. Retuning because 2027 lost is not.
- After copying the zip into a repo, hash the installed files (`hash_installed_standard.py` / `INSTALLED_STANDARD_HASHES.md`) so old-pack agents are visible.

**MUST NOT**

- Quote in-sample or full-history Hypothesis-0 (H0) Profit Factor (PF) as proof of an edge.
- Expand the grid, change timeframe, or add a filter because the exam failed.
- Relax Frozen Version 2.1 gates after seeing the affected Out-Of-Sample (OOS).
- Call walk-forward “done” if the selector could read outer-test metrics.

---

## 7. Where this lives in the pack

- **Zip other hunting agents install:** `C:\projects\BASE CURSOR\TRADING_BOT_CURSOR_RULES_V2.zip`
- Always-on short rule: `.cursor/rules/trading-bot-core.mdc` (Practice vs exam)
- Full nested protocol: `TRADING_BOT_RESEARCH_STANDARD_V2.md` §0.5, §15–16
- Freeze form: `RESEARCH_GENERATION_FREEZE.template.md`
- Gates scored on outer Out-Of-Sample only: `FROZEN_DEFAULT_GATES_V2_1.md` Gate B
