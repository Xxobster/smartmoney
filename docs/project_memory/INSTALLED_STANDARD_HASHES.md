# Installed trading-bot standard hashes

**Written (UTC):** 2026-09-01T12:37:46Z
**Pack zip:** `C:\projects\BASE CURSOR\TRADING_BOT_CURSOR_RULES_V2.zip`
**Pack zip SHA-256:** `58f24065288d4aad8ac5f386edee3df2154a5472f55ffcb67656eb744cc93d96`

Identity files (`IN_SAMPLE_VS_OOS.md`, gates, freeze template) **must MATCH** the zip. If they `DIFFERS_FROM_PACK` or a file is `MISSING`, this agent is on an **old or incomplete** pack — re-copy `C:\projects\BASE CURSOR\TRADING_BOT_CURSOR_RULES_V2.zip` and re-run `python scripts/hash_installed_standard.py`. Core rule / long standard may be a documented repo fork.

| File | SHA-256 | vs pack | Note |
|------|---------|---------|------|
| `TRADING_BOT_RESEARCH_STANDARD_V2.md` | `545661d4b4555484524f981c100d71f1ef306c06cad84a930a2d4b0872daf534` | DIFFERS_FROM_PACK | Repo fork: shorter installed standard than the zip. Must still contain §0.5 and §16.0. Re-bootstrap from the zip to fully align. |
| `IN_SAMPLE_VS_OOS.md` | `2d2a4f98c78a7f07e049c361f82d8cbb8239e9c26c04c9408ac5adf7cd680e4a` | MATCH |  |
| `TP_SL_MAKER.md` | `b8ec084d47615825f9afc1e21c92538b5a4211844870159d439289c124666a5f` | MATCH |  |
| `FROZEN_DEFAULT_GATES_V2_1.md` | `31598f7161bbdd7100f1ff8e3412fbeb904db81ccb1dc1aafbd95ddbb52676d0` | MATCH |  |
| `RESEARCH_GENERATION_FREEZE.template.md` | `2538e9d7727f37c9ef4236ec16d42091aafdf3358ab16910fe7ccefadc94c482` | MATCH |  |
| `trading-bot-core.mdc` | `013963aa2764cf093fd15e539394323947a952107f5211bf2fff7ab1363a2712` | DIFFERS_FROM_PACK | Repo fork: Bybit USDT perpetual fee bullets. Must still contain Practice vs exam (MUST). Not an old pack by itself. |

JSON: `docs/project_memory/INSTALLED_STANDARD_HASHES.json`.

Hypothesis-0 (H0) screens stay `EXPLORATORY_IN_SAMPLE`. A real search needs `RESEARCH_GENERATION_FREEZE.md` filled **before** exam Profit Factor (PF).
