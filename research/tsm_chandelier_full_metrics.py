"""Dump full metrics for tsm-chandelier live units + research baselines."""
from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
REP = ROOT / "artifacts" / "reports" / "tsm_chandelier"
LIVE_DB = REP / "live_vps94_tsm_chandelier_live.sqlite"


def _ms_utc(ms: int | None) -> str | None:
    if ms is None:
        return None
    return datetime.fromtimestamp(int(ms) / 1000, tz=timezone.utc).isoformat()


def live_from_sqlite(db: Path) -> dict:
    con = sqlite3.connect(db)
    con.row_factory = sqlite3.Row
    tables = [r[0] for r in con.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()]
    out: dict = {
        "db_path": str(db),
        "db_mtime_utc": datetime.fromtimestamp(db.stat().st_mtime, tz=timezone.utc).isoformat(),
        "tables": tables,
        "note": "Local copy pulled earlier from VPS94; SSH banner timeout prevented a fresh pull today.",
    }
    for t in tables:
        out[f"count_{t}"] = int(con.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0])

    opens = [dict(r) for r in con.execute("SELECT * FROM open_trades")]
    for o in opens:
        o["entry_utc"] = _ms_utc(o.get("entry_ts_ms"))
    out["open_trades"] = opens

    closed = [dict(r) for r in con.execute("SELECT * FROM closed_trades")]
    # normalize timestamps if present
    for c in closed:
        for k in ("entry_ts_ms", "exit_ts_ms", "created_ts_ms"):
            if k in c and c[k] is not None:
                c[k.replace("_ts_ms", "_utc")] = _ms_utc(c[k])
    out["closed_trades"] = closed

    handled = [dict(r) for r in con.execute("SELECT * FROM handled_entries ORDER BY entry_ts_ms")]
    for h in handled:
        h["entry_utc"] = _ms_utc(h.get("entry_ts_ms"))
    out["handled_entries"] = handled

    ev_counts = [
        dict(r)
        for r in con.execute(
            "SELECT symbol, kind, COUNT(*) AS n FROM events GROUP BY symbol, kind ORDER BY symbol, kind"
        )
    ]
    out["event_counts"] = ev_counts

    # Per-symbol live rollup from closed + open
    symbols = ["BTCUSDT", "ETHUSDT", "SOLUSDT"]
    per = {}
    for sym in symbols:
        c_sym = [c for c in closed if c.get("symbol") == sym]
        o_sym = [o for o in opens if o.get("symbol") == sym]
        pnls = [float(c.get("closed_pnl") or 0) for c in c_sym]
        per[sym] = {
            "n_closed": len(c_sym),
            "n_open": len(o_sym),
            "n_handled_entries": sum(1 for h in handled if h.get("symbol") == sym),
            "realized_pnl_sum": float(sum(pnls)) if pnls else 0.0,
            "closed_trades": c_sym,
            "open_trades": o_sym,
        }
        if pnls:
            wins = [p for p in pnls if p > 0]
            losses = [p for p in pnls if p < 0]
            gp = float(sum(wins))
            gl = float(abs(sum(losses)))
            per[sym].update(
                {
                    "win_rate": float(np.mean([p > 0 for p in pnls])),
                    "expectancy": float(np.mean(pnls)),
                    "profit_factor": (gp / gl) if gl > 0 else (float("inf") if gp > 0 else float("nan")),
                    "best_trade": float(max(pnls)),
                    "worst_trade": float(min(pnls)),
                }
            )
    out["per_symbol_live"] = per

    # funding / equity tables if present
    for tbl in ("funding_events", "funding", "equity_mtm", "wallet_snapshots", "snapshots"):
        if tbl in tables:
            rows = [dict(r) for r in con.execute(f"SELECT * FROM {tbl}")]
            out[tbl] = rows if len(rows) <= 500 else {"n": len(rows), "sample_tail": rows[-20:]}

    # last events
    if "events" in tables:
        out["events_tail"] = [
            dict(r)
            for r in con.execute(
                "SELECT id, ts_utc, symbol, kind, substr(detail_json,1,300) AS detail FROM events ORDER BY id DESC LIMIT 40"
            )
        ]
    return out


def research_bundle() -> dict:
    oos = json.loads((REP / "1h_oos_summary.json").read_text(encoding="utf-8"))
    gate = json.loads((REP / "1h_gate_bcd_summary.json").read_text(encoding="utf-8"))
    monthly = json.loads((REP / "1h_monthly_trade_distribution.json").read_text(encoding="utf-8"))
    freeze = json.loads((REP / "1h_SHADOW_FREEZE.json").read_text(encoding="utf-8"))
    reconcile = json.loads((REP / "live_closed_reconcile_vps94.json").read_text(encoding="utf-8"))

    stitched = {m["symbol"]: m for m in oos.get("stitched_metrics", [])}
    # SOL from monthly file (not in primary freeze)
    sol = monthly.get("sol_status", {})
    per_sym_research = {
        "BTCUSDT": stitched.get("BTCUSDT"),
        "ETHUSDT": stitched.get("ETHUSDT"),
        "SOLUSDT": {
            "symbol": "SOLUSDT",
            "n_trades": sol.get("n_trades"),
            "net_pnl": sol.get("net_pnl"),
            "profit_factor": sol.get("pooled_pf"),
            "status": "exploratory_not_in_primary_freeze",
            "liquidation_status": sol.get("liquidation_status"),
            "avg_trades_per_month": sol.get("avg_trades_per_month"),
            "note": monthly.get("readiness_note", {}).get("SOLUSDT"),
        },
    }
    return {
        "freeze": {
            "freeze_id": freeze.get("freeze_id"),
            "package_hash": freeze.get("package_hash_sha256"),
            "params": freeze.get("logical_seed"),
            "symbols_frozen_primary": freeze.get("symbols_frozen_primary"),
            "maximum_earned_readiness": freeze.get("maximum_earned_readiness"),
        },
        "historical_oos_stitched": {
            "pooled_trades": oos.get("pooled_trades"),
            "net_pnl": oos.get("net_pnl"),
            "pooled_pf": oos.get("pooled_pf"),
            "expectancy": oos.get("expectancy"),
            "win_rate_trade_weighted": oos.get("win_rate_trade_weighted"),
            "sharpe_daily_ann_mean_symbols": oos.get("sharpe_daily_ann_mean_symbols"),
            "hac_sharpe_ann_mean_symbols": oos.get("hac_sharpe_ann_mean_symbols"),
            "max_drawdown": oos.get("max_drawdown"),
            "positive_eligible_fold_fraction": oos.get("positive_eligible_fold_fraction"),
            "n_outer_folds": oos.get("n_outer_folds"),
            "per_symbol": per_sym_research,
            "fold_summaries": oos.get("fold_summaries"),
            "evidence_class": oos.get("evidence_class"),
        },
        "gate_bcd": {
            "maximum_earned_readiness": gate.get("maximum_earned_readiness"),
            "dsr_preregistered": gate.get("dsr", {}).get("dsr_preregistered"),
            "bootstrap_pos_exp": gate.get("bootstrap", {}).get("frac_positive_expectancy"),
            "moderate_stress_pf": gate.get("moderate_stress_2x_slip", {}).get("pooled_pf")
            if isinstance(gate.get("moderate_stress_2x_slip"), dict)
            else None,
            "engine_conformance_green": gate.get("conformance", {}).get("is_green"),
            "liquidation_status": gate.get("baseline_replay", {}).get("liquidation_status"),
        },
        "micro_live_reconcile_asof_2026_08_12": {
            "generated_utc": reconcile.get("generated_utc"),
            "open_trades": reconcile.get("open_trades"),
            "closed_reconcile": reconcile.get("closed_reconcile"),
            "equity_mtm": reconcile.get("equity_mtm"),
            "verdict": reconcile.get("verdict"),
        },
    }


def main() -> None:
    live = live_from_sqlite(LIVE_DB) if LIVE_DB.exists() else {"error": "missing live db"}
    research = research_bundle()
    report = {
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "units": [
            "tsm-chandelier@BTCUSDT",
            "tsm-chandelier@ETHUSDT",
            "tsm-chandelier@SOLUSDT",
        ],
        "account": "Xxobster6",
        "venue": "Bybit USDT linear perp",
        "timeframe": "1h",
        "strategy": "tsm_chandelier",
        "vps_ssh_status": "UNREACHABLE_banner_timeout_ping_ok",
        "research": research,
        "live": live,
    }
    # Enrich gate moderate stress pf if nested differently
    stress = research["gate_bcd"]
    if stress.get("moderate_stress_pf") is None:
        g = json.loads((REP / "1h_gate_bcd_summary.json").read_text(encoding="utf-8"))
        ms = g.get("moderate_stress_2x_slip") or g.get("cost_stress") or {}
        if isinstance(ms, dict):
            stress["moderate_stress_pf"] = ms.get("pooled_pf") or ms.get("pooled_profit_factor")
            if "per_symbol" in ms:
                stress["moderate_stress_per_symbol"] = [
                    {
                        "symbol": x.get("symbol"),
                        "net_pnl": x.get("net_pnl"),
                        "profit_factor": x.get("profit_factor"),
                        "sharpe_ann": x.get("sharpe_ann"),
                    }
                    for x in ms["per_symbol"]
                ]

    path = REP / "live_units_full_metrics.json"
    path.write_text(json.dumps(report, indent=2, default=str), encoding="utf-8")
    # also short sitrep md
    lines = [
        "# tsm-chandelier units — full metrics",
        "",
        f"Generated: {report['generated_utc']}",
        f"VPS SSH: {report['vps_ssh_status']} (live DB mtime: {live.get('db_mtime_utc')})",
        "",
        "## Historical OOS (BTC+ETH freeze, RESEARCH_PROXY)",
        f"- Pooled trades: {research['historical_oos_stitched']['pooled_trades']}",
        f"- Net PnL: {research['historical_oos_stitched']['net_pnl']:.4f}",
        f"- PF: {research['historical_oos_stitched']['pooled_pf']:.4f}",
        f"- Expectancy: {research['historical_oos_stitched']['expectancy']:.4f}",
        f"- WR: {research['historical_oos_stitched']['win_rate_trade_weighted']:.2%}",
        f"- Sharpe ann (mean symbols): {research['historical_oos_stitched']['sharpe_daily_ann_mean_symbols']:.4f}",
        f"- HAC Sharpe: {research['historical_oos_stitched']['hac_sharpe_ann_mean_symbols']:.4f}",
        f"- MDD: {research['historical_oos_stitched']['max_drawdown']:.6f}",
        f"- DSR (preregistered n_trials=1): {research['gate_bcd']['dsr_preregistered']}",
        f"- Bootstrap pos exp: {research['gate_bcd']['bootstrap_pos_exp']}",
        f"- Conformance green: {research['gate_bcd']['engine_conformance_green']}",
        "",
        "## Per-symbol historical stitched",
    ]
    for sym, m in research["historical_oos_stitched"]["per_symbol"].items():
        if not m:
            continue
        lines.append(
            f"- **{sym}**: n={m.get('n_trades')} net={m.get('net_pnl')} pf={m.get('profit_factor')} "
            f"wr={m.get('win_rate')} sharpe={m.get('sharpe_ann')} fees={m.get('total_fees')}"
        )
    lines += ["", "## Micro-live (from local VPS DB copy)"]
    for sym, m in (live.get("per_symbol_live") or {}).items():
        lines.append(
            f"- **{sym}**: closed={m['n_closed']} open={m['n_open']} handled={m['n_handled_entries']} "
            f"realized_sum={m['realized_pnl_sum']:.6f}"
        )
    md = REP / "live_units_full_metrics.md"
    md.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(md.read_text(encoding="utf-8"))
    print(f"wrote {path}")
    print(f"wrote {md}")


if __name__ == "__main__":
    main()
