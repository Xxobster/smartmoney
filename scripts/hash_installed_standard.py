"""Write SHA-256 hashes of the installed trading-bot standard files.

Run from the repository root after copying
`C:\\projects\\BASE CURSOR\\TRADING_BOT_CURSOR_RULES_V2.zip` so later agents can
see whether they are still on an old pack.

  python scripts/hash_installed_standard.py
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PACK_ZIP = Path(r"C:\projects\BASE CURSOR\TRADING_BOT_CURSOR_RULES_V2.zip")
PACK_SUMS = Path(r"C:\projects\BASE CURSOR\_rules_v2_work\SHA256SUMS.txt")

INSTALLED = {
    "TRADING_BOT_RESEARCH_STANDARD_V2.md": ROOT
    / "docs"
    / "project_memory"
    / "TRADING_BOT_RESEARCH_STANDARD_V2.md",
    "IN_SAMPLE_VS_OOS.md": ROOT / "docs" / "project_memory" / "IN_SAMPLE_VS_OOS.md",
    "TP_SL_MAKER.md": ROOT / "docs" / "project_memory" / "TP_SL_MAKER.md",
    "FROZEN_DEFAULT_GATES_V2_1.md": ROOT
    / "docs"
    / "project_memory"
    / "FROZEN_DEFAULT_GATES_V2_1.md",
    "RESEARCH_GENERATION_FREEZE.template.md": ROOT
    / "docs"
    / "project_memory"
    / "RESEARCH_GENERATION_FREEZE.template.md",
    "trading-bot-core.mdc": ROOT / ".cursor" / "rules" / "trading-bot-core.mdc",
}

# Files that must byte-match the zip. Others may be a documented repo fork.
IDENTITY_FILES = {
    "IN_SAMPLE_VS_OOS.md",
    "FROZEN_DEFAULT_GATES_V2_1.md",
    "RESEARCH_GENERATION_FREEZE.template.md",
    "TP_SL_MAKER.md",
}

FORK_NOTES = {
    "trading-bot-core.mdc": (
        "Repo fork: Bybit USDT perpetual fee bullets. Must still contain "
        "Practice vs exam (MUST). Not an old pack by itself."
    ),
    "TRADING_BOT_RESEARCH_STANDARD_V2.md": (
        "Repo fork: shorter installed standard than the zip. Must still contain "
        "§0.5 and §16.0. Re-bootstrap from the zip to fully align."
    ),
}


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    h.update(path.read_bytes())
    return h.hexdigest()


def pack_expected() -> dict[str, str]:
    out: dict[str, str] = {}
    if not PACK_SUMS.is_file():
        return out
    for line in PACK_SUMS.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or "  " not in line:
            continue
        digest, name = line.split("  ", 1)
        out[name.strip()] = digest.strip().lower()
    return out


def main() -> None:
    expected = pack_expected()
    rows: list[dict[str, str]] = []
    mismatches: list[str] = []
    for name, path in INSTALLED.items():
        if not path.is_file():
            rows.append({"file": name, "path": str(path), "status": "MISSING"})
            mismatches.append(name)
            continue
        digest = sha256_file(path)
        pack_name = "trading-bot-core.mdc" if name.endswith(".mdc") else name
        exp = expected.get(pack_name)
        match = "n/a" if exp is None else ("MATCH" if exp == digest else "DIFFERS_FROM_PACK")
        if match == "DIFFERS_FROM_PACK" and name in IDENTITY_FILES:
            mismatches.append(name)
        rows.append(
            {
                "file": name,
                "path": str(path),
                "sha256": digest,
                "pack_sha256": exp or "",
                "vs_pack": match,
                "note": FORK_NOTES.get(name, ""),
            }
        )
    zip_hash = sha256_file(PACK_ZIP) if PACK_ZIP.is_file() else ""
    payload = {
        "written_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "pack_zip": str(PACK_ZIP),
        "pack_zip_sha256": zip_hash,
        "files": rows,
        "mismatches": mismatches,
    }
    out_md = ROOT / "docs" / "project_memory" / "INSTALLED_STANDARD_HASHES.md"
    out_json = ROOT / "docs" / "project_memory" / "INSTALLED_STANDARD_HASHES.json"
    lines = [
        "# Installed trading-bot standard hashes",
        "",
        f"**Written (UTC):** {payload['written_utc']}",
        f"**Pack zip:** `{PACK_ZIP}`",
        f"**Pack zip SHA-256:** `{zip_hash or 'ZIP_MISSING'}`",
        "",
        "Identity files (`IN_SAMPLE_VS_OOS.md`, gates, freeze template) **must MATCH** the zip. If they `DIFFERS_FROM_PACK` or a file is `MISSING`, this agent is on an **old or incomplete** pack — re-copy `C:\\projects\\BASE CURSOR\\TRADING_BOT_CURSOR_RULES_V2.zip` and re-run `python scripts/hash_installed_standard.py`. Core rule / long standard may be a documented repo fork.",
        "",
        "| File | SHA-256 | vs pack | Note |",
        "|------|---------|---------|------|",
    ]
    for r in rows:
        digest = r.get("sha256", "")
        note = r.get("note", "").replace("|", "/")
        lines.append(
            f"| `{r['file']}` | `{digest}` | {r.get('status') or r.get('vs_pack')} | {note} |"
        )
    lines.extend(
        [
            "",
            "JSON: `docs/project_memory/INSTALLED_STANDARD_HASHES.json`.",
            "",
            "Hypothesis-0 (H0) screens stay `EXPLORATORY_IN_SAMPLE`. A real search needs `RESEARCH_GENERATION_FREEZE.md` filled **before** exam Profit Factor (PF).",
            "",
        ]
    )
    out_md.write_text("\n".join(lines), encoding="utf-8")
    out_json.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(out_md)
    print("mismatches:", mismatches or "none")


if __name__ == "__main__":
    main()
