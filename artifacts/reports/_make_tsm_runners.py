"""Generate standard leakage/baseline/build_features runners for a tsm_* package."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def write_package(slug: str, tfs: tuple[str, ...], leak_tf: str, holds: dict[str, int]) -> None:
    pkg = ROOT / "strategies" / slug
    pkg.mkdir(parents=True, exist_ok=True)
    (pkg / "build_features.py").write_text(
        f'''from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from strategies.{slug}.signals import build_signal_frame


def build_features(ohlcv: pd.DataFrame, *, interval: str = "{leak_tf}") -> pd.DataFrame:
    del interval
    feat = build_signal_frame(ohlcv.sort_values("ts_ms").reset_index(drop=True))
    keep = [c for c in feat.columns if c not in {{"stop_price", "target_price"}} or c.startswith("_")]
    # keep causal feature cols used by leakage (exclude stop/target geometry)
    drop = {{"stop_price", "target_price"}}
    cols = [c for c in feat.columns if c not in drop]
    return feat[cols].copy()
''',
        encoding="utf-8",
    )
    (pkg / "run_leakage.py").write_text(
        f'''from __future__ import annotations

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
from strategies.{slug}.build_features import build_features


def main() -> None:
    df = load_ohlcv(research_db(), "BTCUSDT", "{leak_tf}")
    if len(df) > 8000:
        df = df.iloc[-8000:].reset_index(drop=True)
    out_dir = ROOT / "artifacts" / "reports" / "{slug}"
    out_dir.mkdir(parents=True, exist_ok=True)
    report = run_leakage_audit(
        ohlcv=df, build_features=build_features, interval="{leak_tf}",
        registry_path=str(out_dir / "leakage_registry.json"),
    )
    summary = {{"ok": bool(report.ok), "summary": report.summary()}}
    (out_dir / "leakage_h0.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(summary["ok"], summary["summary"])
    if not report.ok:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
''',
        encoding="utf-8",
    )
    tfs_repr = ", ".join(f'"{t}"' for t in tfs)
    holds_repr = ", ".join(f'"{k}": {v}' for k, v in holds.items())
    (pkg / "run_baseline.py").write_text(
        f'''from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tradesim.ensure_source import prefer_botsgeneral_tradesim

prefer_botsgeneral_tradesim()

from engine.data_loader import load_ohlcv, research_db
from engine.tradesim_adapter import PROJECT_STARTING_EQUITY_USDT, df_to_barseries
from tradesim import run_backtest
from strategies.{slug}.signals import (
    STRATEGY_ID,
    STRATEGY_VERSION,
    build_signal_frame,
    to_tradesim_signals,
)

HOLDS = {{{holds_repr}}}


def run_one(symbol: str, timeframe: str) -> dict:
    db = research_db()
    bars_df = load_ohlcv(db, symbol, timeframe)
    if bars_df.empty:
        return {{"symbol": symbol, "timeframe": timeframe, "status": "no_data", "n_trades": 0,
                "readiness": "LIVE_STOP / RESEARCH_ONLY"}}
    touch = load_ohlcv(db, symbol, "1m")
    feat = build_signal_frame(bars_df)
    signals = to_tradesim_signals(feat, symbol, max_hold_bars=HOLDS.get(timeframe, 36))
    if not signals:
        return {{"symbol": symbol, "timeframe": timeframe, "n_trades": 0, "status": "no_signals",
                "readiness": "LIVE_STOP / RESEARCH_ONLY"}}
    bundle = run_backtest(
        strategy_id=f"{{STRATEGY_ID}}_{{symbol.lower()}}_{{timeframe}}",
        strategy_version=STRATEGY_VERSION,
        bars=df_to_barseries(feat, timeframe, symbol),
        symbol=symbol,
        signals=signals,
        touch_bars=df_to_barseries(touch, "1m", symbol) if not touch.empty else None,
        starting_equity=PROJECT_STARTING_EQUITY_USDT,
        plot=False,
        print_headline=True,
        store_path=None,
    )
    m = bundle.metrics
    return {{
        "symbol": symbol,
        "timeframe": timeframe,
        "n_trades": int(m.n_trades),
        "profit_factor": float(m.profit_factor),
        "sharpe_ann": float(m.sharpe.annualised) if m.sharpe else 0.0,
        "hac_sharpe_ann": float(m.sharpe.hac_annualised) if m.sharpe else 0.0,
        "max_drawdown": float(m.max_drawdown_pct),
        "win_rate": float(m.win_rate),
        "net_pnl": float(m.net_pnl),
        "status": "ok",
        "readiness": "LIVE_STOP / RESEARCH_ONLY",
        "evidence_class": "RESEARCH_PROXY",
        "headline": bundle.headline,
    }}


def main() -> None:
    out_dir = ROOT / "artifacts" / "reports" / "{slug}"
    out_dir.mkdir(parents=True, exist_ok=True)
    print("=== {slug} H0 ===\\nMaximum earned readiness: LIVE_STOP / RESEARCH_ONLY\\n")
    results = []
    for tf in ({tfs_repr},):
        for sym in ("BTCUSDT", "ETHUSDT"):
            print(f"--- {{sym}} {{tf}} ---")
            m = run_one(sym, tf)
            results.append(m)
            print(f"  n={{m.get('n_trades')}} PF={{m.get('profit_factor')}} WR={{m.get('win_rate')}} status={{m.get('status')}}")
    path = out_dir / "baseline_h0.json"
    path.write_text(json.dumps(results, indent=2, default=str), encoding="utf-8")
    print("Wrote", path)


if __name__ == "__main__":
    main()
''',
        encoding="utf-8",
    )
    print("wrote runners", slug)


if __name__ == "__main__":
    write_package("tsm_macd_trend", ("1h", "4h"), "1h", {"1h": 48, "4h": 24})
    write_package("tsm_vol_climax", ("1h", "4h"), "1h", {"1h": 24, "4h": 18})
    write_package("tsm_chandelier", ("15m", "1h"), "1h", {"15m": 48, "1h": 36})
