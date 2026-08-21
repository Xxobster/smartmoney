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
from strategies.tsm_breakout_score.build_features import build_features


def main() -> None:
    df = load_ohlcv(research_db(), "BTCUSDT", "15m")
    if len(df) > 12000:
        df = df.iloc[-12000:].reset_index(drop=True)
    out_dir = ROOT / "artifacts" / "reports" / "tsm_breakout_score"
    out_dir.mkdir(parents=True, exist_ok=True)
    report = run_leakage_audit(
        ohlcv=df, build_features=build_features, interval="15m",
        registry_path=str(out_dir / "leakage_registry.json"),
    )
    summary = {"ok": bool(report.ok), "summary": report.summary()}
    (out_dir / "leakage_h0.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(summary["ok"], summary["summary"])
    if not report.ok:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
