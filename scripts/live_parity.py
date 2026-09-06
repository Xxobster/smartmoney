#!/usr/bin/env python3
"""One-command live vs backtest parity for smartmoney bots on VPS94.

Only bots from this project (currently tsm_chandelier). Fetches latest
Binance 1h+1m candles locally, pulls live state from the VPS, compares
candles / indicators / signals / exits, and prints the verdict.

Usage:
  python scripts/live_parity.py
  python scripts/live_parity.py --skip-fetch
  python scripts/live_parity.py --plot
  python scripts/live_parity.py --host eventactivities-vps
"""
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "research"))
from live_parity_closeness import fmt_pct, format_glimpse_table  # noqa: E402
OUT = ROOT / "artifacts" / "reports" / "tsm_chandelier"
LIVE_DB = OUT / "live_vps94_tsm_chandelier_live.sqlite"
SSH_DEFAULT = "eventactivities-vps"
VPS_LIVE_DB = "/opt/tsm-chandelier/data/live/tsm_chandelier_live.sqlite"


def run(cmd: list[str] | str, *, cwd: Path | None = None, check: bool = True) -> subprocess.CompletedProcess:
    print("+", cmd if isinstance(cmd, str) else " ".join(cmd), flush=True)
    return subprocess.run(
        cmd,
        cwd=str(cwd or ROOT),
        check=check,
        shell=isinstance(cmd, str),
    )


def pull_live_db(host: str) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    remote = f"{host}:{VPS_LIVE_DB}"
    print(f"Pulling live DB {remote} -> {LIVE_DB}", flush=True)
    run(["scp", remote, str(LIVE_DB)])


def refresh_candles() -> None:
    run([sys.executable, str(ROOT / "research" / "refresh_research_ohlcv_from_binance.py")])


def run_compare() -> Path:
    run([sys.executable, str(ROOT / "research" / "compare_live_vs_bt_full_vps94.py")])
    latest = OUT / "live_vs_bt_full_latest.json"
    if latest.exists():
        return latest
    newest = sorted(OUT.glob("live_vs_bt_full_*.json"), key=lambda p: p.stat().st_mtime)
    if not newest:
        raise SystemExit("compare finished but no live_vs_bt_full_*.json found")
    return newest[-1]


def maybe_plot() -> None:
    plot = ROOT / "research" / "plot_live_vs_backtest_finplot.py"
    if not plot.exists():
        print("plot script missing — skip", flush=True)
        return
    # non-blocking: user can close the window
    subprocess.Popen([sys.executable, str(plot)], cwd=str(ROOT))


def print_verdict(path: Path) -> int:
    data = json.loads(path.read_text(encoding="utf-8"))
    v = data.get("verdict") or {}
    print("\n======== LIVE PARITY SITREP ========", flush=True)
    print("Generated:", data.get("generated_utc") or datetime.now(timezone.utc).isoformat(), flush=True)
    print("Combined JSON:", path, flush=True)
    print("Maximum earned readiness:", v.get("maximum_earned_readiness"), flush=True)
    print("Evidence class:", data.get("evidence_class"), flush=True)
    print("Principal blocker:", v.get("principal_blocker") or data.get("principal_blocker"), flush=True)
    print("Material logic bug:", v.get("material_logic_bug"), flush=True)

    acc_json = OUT / "by_account" / "Xxobster6.json"
    acc_md = OUT / "by_account" / "Xxobster6.md"
    bot_dir = OUT / "by_bot"

    glimpse_rows: list[dict] = []
    if bot_dir.exists():
        for jp in sorted(bot_dir.glob("*.json")):
            bot = json.loads(jp.read_text(encoding="utf-8"))
            c = bot.get("closeness") or (bot.get("verdict") or {}).get("closeness") or {}
            glimpse_rows.append(
                {
                    "label": f"{bot.get('account')} {bot.get('bot_unit')}",
                    **c,
                }
            )
    if acc_json.exists():
        acc = json.loads(acc_json.read_text(encoding="utf-8"))
        c = acc.get("closeness") or {}
        glimpse_rows.append({"label": f"ACCOUNT {acc.get('account')} mean", **c})
        print("\n" + format_glimpse_table(glimpse_rows, title="CLOSENESS  live vs backtest  (logic %; fill prices allow designed slip)"), flush=True)
        print("\n--- ACCOUNT", acc.get("account"), "---", flush=True)
        print("  pack:", acc.get("pack_id"), flush=True)
        print("  bots:", ", ".join(acc.get("bots") or []), flush=True)
        print("  closed / open:", acc.get("closed_trade_count"), "/", acc.get("open_trade_count"), flush=True)
        net = acc.get("closed_net_pnl_usdt")
        if net is not None:
            print(f"  closed net USDT: {float(net):+.4f}", flush=True)
        print("  working as specified:", acc.get("strategy_working_as_specified"), flush=True)
        print("  report:", acc_md if acc_md.exists() else acc_json, flush=True)
    elif glimpse_rows:
        print("\n" + format_glimpse_table(glimpse_rows, title="CLOSENESS  live vs backtest"), flush=True)
    elif acc_md.exists():
        print("Account report:", acc_md, flush=True)

    if bot_dir.exists():
        for jp in sorted(bot_dir.glob("*.json")):
            bot = json.loads(jp.read_text(encoding="utf-8"))
            bv = bot.get("verdict") or {}
            c = bot.get("closeness") or bv.get("closeness") or {}
            md = jp.with_suffix(".md")
            print(f"\n--- BOT {bot.get('bot_unit')} ({bot.get('symbol')}) ---", flush=True)
            print("  account:", bot.get("account"), flush=True)
            print(
                "  closeness: candles {c}  calculations {k}  signals {s}  entries/exits {e}  fill prices {f}".format(
                    c=fmt_pct(c.get("candles_pct")),
                    k=fmt_pct(c.get("calculations_pct")),
                    s=fmt_pct(c.get("signals_pct")),
                    e=fmt_pct(c.get("entries_exits_pct")),
                    f=fmt_pct(c.get("fill_price_pct")),
                ),
                flush=True,
            )
            print("  freeze role:", bot.get("freeze_role"), flush=True)
            print("  working as specified:", bv.get("strategy_working_as_specified"), flush=True)
            print("  closed / open:", bv.get("closed_trade_count"), "/", bv.get("open_trade_count"), flush=True)
            cnet = bv.get("closed_net_pnl_usdt")
            if cnet is not None:
                print(f"  closed net USDT: {float(cnet):+.4f}", flush=True)
            print("  report:", md if md.exists() else jp, flush=True)

    md = path.with_suffix(".md")
    if md.exists():
        print("\nCombined markdown:", md, flush=True)
    if v.get("material_logic_bug"):
        print("\nACTION: material live/backtest mismatch — investigate and fix (safe fixes only).", flush=True)
        return 2
    print("\nOK: no material logic bug. Slippage / venue differences may remain by design.", flush=True)
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description="smartmoney live vs backtest parity (VPS94 tsm_chandelier)")
    ap.add_argument("--host", default=SSH_DEFAULT, help="SSH host alias for VPS94")
    ap.add_argument("--skip-fetch", action="store_true", help="skip VPS live-DB pull and candle refresh")
    ap.add_argument("--skip-pull", action="store_true", help="skip VPS live-DB pull only")
    ap.add_argument("--skip-candles", action="store_true", help="skip local 1h/1m candle refresh only")
    ap.add_argument("--plot", action="store_true", help="open finplot live (cyan) vs backtest (orange)")
    ap.add_argument("--dry-run", action="store_true", help="print steps only")
    args = ap.parse_args()

    if shutil.which("scp") is None and not args.skip_fetch and not args.skip_pull:
        print("WARN: scp not found — use --skip-pull if live DB already local", flush=True)

    steps = []
    if not args.skip_fetch and not args.skip_pull:
        steps.append(("pull_live_db", lambda: pull_live_db(args.host)))
    if not args.skip_fetch and not args.skip_candles:
        steps.append(("refresh_candles_1h_1m", refresh_candles))
    steps.append(("compare", None))

    print("live_parity scope: tsm_chandelier @", args.host, flush=True)
    if args.dry_run:
        for name, _ in steps:
            print(" would:", name, flush=True)
        if args.plot:
            print(" would: plot", flush=True)
        return 0

    for name, fn in steps:
        if fn is None:
            continue
        print(f"--- {name} ---", flush=True)
        fn()

    print("--- compare ---", flush=True)
    report = run_compare()
    code = print_verdict(report)
    if args.plot:
        print("--- plot ---", flush=True)
        maybe_plot()
    return code


if __name__ == "__main__":
    raise SystemExit(main())
