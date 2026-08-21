"""Run botsgeneral leakage audit on TSM liquidity H0 feature builder."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from leakage.ensure_source import prefer_botsgeneral_leakage

prefer_botsgeneral_leakage()

from leakage import run_leakage_audit

from engine.data_loader import load_ohlcv, research_db
from strategies.tsm_liquidity_sweep.build_features import build_features


def main() -> None:
    db = research_db()
    # Use a contiguous recent slice for speed; causality checks are length-robust.
    df = load_ohlcv(db, "BTCUSDT", "15m")
    if len(df) > 8000:
        df = df.iloc[-8000:].reset_index(drop=True)
    out_dir = ROOT / "artifacts" / "reports" / "tsm_liquidity_sweep"
    out_dir.mkdir(parents=True, exist_ok=True)
    registry = out_dir / "leakage_registry.json"
    report = run_leakage_audit(
        ohlcv=df,
        build_features=build_features,
        interval="15m",
        registry_path=str(registry),
    )
    summary = {
        "ok": bool(report.ok),
        "summary": report.summary() if hasattr(report, "summary") else str(report),
        "n_bars": len(df),
        "symbol": "BTCUSDT",
        "timeframe": "15m",
    }
    # Persist richer detail when available
    for attr in ("findings", "hard_fails", "checks"):
        if hasattr(report, attr):
            try:
                summary[attr] = getattr(report, attr)
            except Exception:
                pass
    path = out_dir / "leakage_h0.json"
    path.write_text(json.dumps(summary, indent=2, default=str), encoding="utf-8")
    md = out_dir.parent.parent.parent / "strategies" / "tsm_liquidity_sweep" / "LEAKAGE.md"
    # write next to strategy package
    md = ROOT / "strategies" / "tsm_liquidity_sweep" / "LEAKAGE.md"
    md.write_text(
        "# Leakage audit — tsm_liquidity_sweep H0\n\n"
        f"- **ok:** `{summary['ok']}`\n"
        f"- **bars:** {summary['n_bars']} BTCUSDT 15m (tail slice)\n"
        f"- **registry:** `{registry}`\n"
        f"- **json:** `{path}`\n\n"
        f"```\n{summary.get('summary')}\n```\n",
        encoding="utf-8",
    )
    print(summary["ok"], summary.get("summary"))
    if not report.ok:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
