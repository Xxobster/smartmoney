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
from strategies.tsm_flag_ema2155.build_features import build_features


def main() -> None:
    df = load_ohlcv(research_db(), "BTCUSDT", "1h")
    if len(df) > 6000:
        df = df.iloc[-6000:].reset_index(drop=True)
    out_dir = ROOT / "artifacts" / "reports" / "tsm_flag_ema2155"
    out_dir.mkdir(parents=True, exist_ok=True)
    report = run_leakage_audit(
        ohlcv=df, build_features=build_features, interval="1h",
        registry_path=str(out_dir / "leakage_registry.json"),
    )
    summary = {"ok": bool(report.ok), "summary": report.summary()}
    (out_dir / "leakage_h0.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(summary["ok"], summary["summary"])
    if not report.ok:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
