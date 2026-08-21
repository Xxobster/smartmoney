"""Readiness sitrep from registry + OOS summary."""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

from paths import REPORTS, ensure_artifact_dirs
from research.registry import TrialRegistry


def build_sitrep() -> dict:
    ensure_artifact_dirs()
    REPORTS.mkdir(parents=True, exist_ok=True)
    oos_path = REPORTS / "oos_summary.json"
    search_path = REPORTS / "search_summary.json"
    oos = json.loads(oos_path.read_text(encoding="utf-8")) if oos_path.exists() else {}
    search = json.loads(search_path.read_text(encoding="utf-8")) if search_path.exists() else {}
    reg = TrialRegistry()
    freeze = reg.latest_freeze()
    n_trials = reg.count_trials()
    reg.close()

    readiness = oos.get("readiness", "LIVE_STOP_RESEARCH_ONLY")
    sitrep = {
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "maximum_earned_readiness": readiness,
        "evidence_class": oos.get("evidence_class", "none"),
        "principal_blocker": oos.get("principal_blocker"),
        "authorization": {
            "research": True,
            "shadow": False,
            "micro_live": False,
            "deployment": False,
            "note": "Readiness never equals authorization. User must approve live actions.",
        },
        "search": search,
        "oos": oos,
        "freeze": freeze,
        "registry_trials": n_trials,
        "next_bounded_action": (
            "If gates failed: inspect principal_blocker, fix engine or abandon family — "
            "do NOT expand search after viewing OOS. If SHADOW_READY: request explicit "
            "user authorization before any shadow deployment."
        ),
    }
    out = REPORTS / "sitrep.json"
    out.write_text(json.dumps(sitrep, indent=2, default=str), encoding="utf-8")
    md = REPORTS / "sitrep.md"
    md.write_text(
        "\n".join(
            [
                f"# Sitrep — {sitrep['generated_utc']}",
                "",
                f"**Maximum earned readiness:** `{readiness}`",
                f"**Evidence class:** `{sitrep['evidence_class']}`",
                f"**Principal blocker:** `{sitrep['principal_blocker']}`",
                f"**Registry trials:** {n_trials}",
                f"**Freeze hash:** `{freeze['params_hash'] if freeze else None}`",
                "",
                "## Authorization",
                "Default remains `LIVE_STOP / RESEARCH_ONLY`. No deployment without explicit user approval.",
                "",
                "## Next bounded action",
                sitrep["next_bounded_action"],
                "",
            ]
        ),
        encoding="utf-8",
    )
    print(md.read_text(encoding="utf-8"))
    return sitrep


def main() -> None:
    build_sitrep()


if __name__ == "__main__":
    main()
