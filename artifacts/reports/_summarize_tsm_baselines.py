import json
from pathlib import Path

base = Path(__file__).resolve().parent
for d in sorted(base.glob("tsm_*")):
    p = d / "baseline_h0.json"
    print("==", d.name, "exists", p.exists())
    if not p.exists():
        continue
    rows = json.loads(p.read_text(encoding="utf-8"))
    for r in rows:
        print(
            f"  {r.get('symbol'):8} {str(r.get('timeframe', '?')):4} "
            f"n={r.get('n_trades')} PF={r.get('profit_factor')} "
            f"WR={r.get('win_rate')} status={r.get('status')}"
        )
