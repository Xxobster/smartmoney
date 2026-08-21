"""Collect key metrics from all tsm_* baselines (+ OOS if present)."""
from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
REPORTS = ROOT / "artifacts" / "reports"
OUT_JSON = REPORTS / "tsm_all_metrics.json"
OUT_CSV = REPORTS / "tsm_all_metrics.csv"

HEADLINE_KEYS = [
    ("trades_per_month", r"([\d.]+)/month"),
    ("n_trades_headline", r"trades\s*:\s*(\d+)"),
    ("net_pnl", r"net PnL\s*:\s*([-\d.,]+)"),
    ("profit_factor", r"profit factor\s*:\s*([\d.]+|inf)"),
    ("win_rate", r"win rate\s*:\s*([\d.]+)%"),
    ("sharpe_ann", r"Sharpe annualised\s*:\s*([-\d.]+)"),
    ("hac_sharpe_ann", r"Sharpe HAC raw/ann\s*:\s*[-\d.]+\s*/\s*([-\d.]+)"),
    ("max_drawdown_pct", r"max drawdown \(MTM\)\s*:[^\n]*?\(([\d.]+)%\)"),
    ("expectancy", r"expectancy\s*:\s*([-\d.]+)\s*USDT"),
    ("fees", r"fees / slip / fund\s*:\s*([\d.]+)"),
]


def parse_headline(h: str) -> dict:
    out = {}
    if not h:
        return out
    for key, pat in HEADLINE_KEYS:
        m = re.search(pat, h, flags=re.I)
        if not m:
            continue
        raw = m.group(1).replace(",", "")
        try:
            out[key] = float(raw)
        except ValueError:
            out[key] = raw
    if "win_rate" in out and out["win_rate"] > 1.5:
        out["win_rate"] = out["win_rate"] / 100.0
    if "max_drawdown_pct" in out and out["max_drawdown_pct"] > 1.5:
        out["max_drawdown_pct"] = out["max_drawdown_pct"] / 100.0
    return out


def row_from_baseline(strategy: str, r: dict) -> dict:
    h = parse_headline(str(r.get("headline") or ""))
    symbol = r.get("symbol") or "?"
    tf = r.get("timeframe") or r.get("ltf") or "?"
    n = r.get("n_trades", h.get("n_trades_headline"))
    tpm = r.get("trades_per_month", h.get("trades_per_month"))
    if tpm is None and n is not None:
        # crude fallback if span unknown
        tpm = None
    pf = r.get("profit_factor", h.get("profit_factor"))
    wr = r.get("win_rate", h.get("win_rate"))
    sharpe = r.get("sharpe_ann", h.get("sharpe_ann"))
    hac = r.get("hac_sharpe_ann", h.get("hac_sharpe_ann"))
    mdd = r.get("max_drawdown", h.get("max_drawdown_pct"))
    pnl = r.get("net_pnl", h.get("net_pnl"))
    exp = r.get("expectancy", h.get("expectancy"))
    return {
        "source": "full_history_baseline",
        "strategy": strategy,
        "symbol": symbol,
        "timeframe": tf,
        "n_trades": n,
        "trades_per_month": tpm,
        "profit_factor": pf,
        "win_rate": wr,
        "net_pnl": pnl,
        "expectancy": exp,
        "sharpe_ann": sharpe,
        "hac_sharpe_ann": hac,
        "max_drawdown": mdd,
        "status": r.get("status", "ok"),
        "readiness": r.get("readiness", "LIVE_STOP / RESEARCH_ONLY"),
    }


def main() -> None:
    rows = []
    for d in sorted(REPORTS.glob("tsm_*")):
        if not d.is_dir():
            continue
        base = d / "baseline_h0.json"
        if base.exists():
            data = json.loads(base.read_text(encoding="utf-8"))
            for r in data:
                rows.append(row_from_baseline(d.name, r))
        for oos in d.glob("*_oos_summary.json"):
            s = json.loads(oos.read_text(encoding="utf-8"))
            # pooled row
            tpm = None
            # estimate from fold span if present (symbols share one calendar)
            folds = s.get("fold_summaries") or []
            if folds and s.get("pooled_trades"):
                cal_days = 0.0
                for f in folds:
                    cal_days += max((f.get("test_end_ms", 0) - f.get("test_start_ms", 0)) / 86_400_000, 0)
                if cal_days > 0:
                    tpm = float(s["pooled_trades"]) / (cal_days / 30.437)
            rows.append(
                {
                    "source": "nested_outer_oos_stitched",
                    "strategy": d.name,
                    "symbol": "+".join(s.get("symbols") or []),
                    "timeframe": s.get("timeframe") or oos.name.split("_")[0],
                    "n_trades": s.get("pooled_trades"),
                    "trades_per_month": tpm,
                    "profit_factor": s.get("pooled_pf"),
                    "win_rate": s.get("win_rate_trade_weighted"),
                    "net_pnl": s.get("net_pnl"),
                    "expectancy": s.get("expectancy"),
                    "sharpe_ann": s.get("sharpe_daily_ann_mean_symbols"),
                    "hac_sharpe_ann": s.get("hac_sharpe_ann_mean_symbols"),
                    "max_drawdown": s.get("max_drawdown"),
                    "status": s.get("maximum_earned_readiness"),
                    "readiness": s.get("maximum_earned_readiness"),
                    "principal_blocker": s.get("principal_blocker"),
                }
            )
            for sm in s.get("stitched_metrics") or []:
                rows.append(
                    {
                        "source": "nested_outer_oos_stitched_symbol",
                        "strategy": d.name,
                        "symbol": sm.get("symbol"),
                        "timeframe": s.get("timeframe"),
                        "n_trades": sm.get("n_trades"),
                        "trades_per_month": None,
                        "profit_factor": sm.get("profit_factor"),
                        "win_rate": sm.get("win_rate"),
                        "net_pnl": sm.get("net_pnl"),
                        "expectancy": sm.get("expectancy"),
                        "sharpe_ann": sm.get("sharpe_ann"),
                        "hac_sharpe_ann": sm.get("hac_sharpe_ann"),
                        "max_drawdown": sm.get("max_drawdown"),
                        "status": "oos_symbol",
                        "readiness": s.get("maximum_earned_readiness"),
                    }
                )

    OUT_JSON.write_text(json.dumps(rows, indent=2, default=str), encoding="utf-8")
    # CSV
    cols = [
        "source",
        "strategy",
        "symbol",
        "timeframe",
        "n_trades",
        "trades_per_month",
        "profit_factor",
        "win_rate",
        "net_pnl",
        "expectancy",
        "sharpe_ann",
        "hac_sharpe_ann",
        "max_drawdown",
        "status",
        "readiness",
        "principal_blocker",
    ]
    lines = [",".join(cols)]
    for r in rows:
        lines.append(
            ",".join(
                "" if r.get(c) is None else str(r.get(c)).replace(",", ";")
                for c in cols
            )
        )
    OUT_CSV.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"rows={len(rows)} -> {OUT_JSON}")
    for r in rows:
        if r["source"] != "full_history_baseline" and "symbol" in str(r.get("source")):
            continue
        if r["source"] not in ("full_history_baseline", "nested_outer_oos_stitched"):
            continue
        print(
            f"{r['source'][:12]:12} {r['strategy']:28} {r['symbol']:16} {str(r['timeframe']):4} "
            f"n={r['n_trades']} tpm={r['trades_per_month']} PF={r['profit_factor']} WR={r['win_rate']} "
            f"Sharpe={r['sharpe_ann']}"
        )


if __name__ == "__main__":
    main()
