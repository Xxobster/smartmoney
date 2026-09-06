"""EXEC-021 fleet: 1-minute fill clock + frozen Post-Only offset, all packs.

Wrong old test: 1-minute bars only from 2026-08-01, so 2020–2026 take-profit/stop
used the decision-bar convention (stop-first). Resting limits must not fill at the
decision-bar open if the 1-minute path has not touched them yet.

This is a simulator-correctness retest of frozen recipes, not a parameter search.
Limit offset is the engine-guide example 0.0005, frozen.

Live in this repo: tsm_chandelier on VPS94 / Xxobster6 (market entry). That pack
is also run as taker_market (live match) and exec021_limit (if switched to Post-Only).
"""

from __future__ import annotations

import ast
import importlib
import inspect
import json
import math
import re
import sys
import traceback
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tradesim.ensure_source import prefer_botsgeneral_tradesim

prefer_botsgeneral_tradesim()

from engine.data_loader import research_db
from strategies.common.h0_baseline import (  # noqa: E402
    H0_EVIDENCE_CLASS,
    H0_READINESS,
    LIMIT_OFFSET_FROZEN,
    MIN_TOUCH_COVERAGE,
    _cached_ohlcv,
    run_h0_matrix,
    run_one_side,
    touch_coverage_frac,
)

LIVE_PACKS = {
    "tsm_chandelier": {
        "vps": "94.156.189.76 / ln1",
        "account": "Xxobster6",
        "live_symbols": ("BTCUSDT", "ETHUSDT", "SOLUSDT"),
        "live_timeframe": "1h",
        "entry": "market",
    }
}

OUT_DIR = ROOT / "artifacts" / "reports" / "exec021_fleet"
CHECKPOINT = OUT_DIR / "checkpoint.json"
COVERAGE_SYMBOLS = ("BTCUSDT", "ETHUSDT", "SOLUSDT")
COVERAGE_TF = "1h"


def _literal_assign(text: str, name: str):
    m = re.search(rf"^{name}\s*=\s*(.+)$", text, re.M)
    if not m:
        return None
    try:
        return ast.literal_eval(m.group(1).strip())
    except (SyntaxError, ValueError):
        return None


def _discover_timeframes(rb: str) -> tuple[str, ...]:
    t = _literal_assign(rb, "TIMEFRAMES")
    if t:
        return tuple(t)
    tfs: list[str] = []
    for block in re.findall(r"for tf in \(([^)]+)\)", rb):
        tfs.extend(re.findall(r"['\"](\w+)['\"]", block))
    if tfs:
        return tuple(dict.fromkeys(tfs))
    tfs = re.findall(r'run_one\(\s*\w+\s*,\s*[\'"](\w+)[\'"]', rb)
    if tfs:
        return tuple(dict.fromkeys(tfs))
    loaded = [
        x
        for x in re.findall(r'load_ohlcv\(\s*db\s*,\s*symbol\s*,\s*[\'"](\w+)[\'"]', rb)
        if x != "1m"
    ]
    if loaded:
        return tuple(dict.fromkeys(loaded))
    return ("1h",)


def _default_holds(timeframes: tuple[str, ...], pack: str) -> dict[str, int]:
    holds = {}
    for tf in timeframes:
        holds[tf] = {"5m": 48, "15m": 48, "30m": 32, "1h": 48, "4h": 48, "1d": 40}.get(
            tf, 48
        )
    if pack == "tsm_chandelier":
        holds["1h"] = 36
        holds["15m"] = 48
    if pack == "algovibes_eth_dip":
        holds["1h"] = 5
        holds["4h"] = 5
    if pack == "tsm_london_opening_channel":
        holds["1h"] = 24
    if pack == "tsm_rsi_adx_ema_scalp":
        holds["5m"] = 24
        holds["15m"] = 16
    if pack == "tsm_hilo_ha_adx":
        holds["5m"] = 48
        holds["15m"] = 48
    return holds


def discover_pack(pack: str) -> dict:
    base = ROOT / "strategies" / pack
    rb = (base / "run_baseline.py").read_text(encoding="utf-8")
    sig = importlib.import_module(f"strategies.{pack}.signals")
    symbols = _literal_assign(rb, "SYMBOLS") or ("BTCUSDT", "ETHUSDT")
    timeframes = _discover_timeframes(rb)
    holds = _literal_assign(rb, "HOLDS") or {}
    if not holds:
        holds = _default_holds(timeframes, pack)
    else:
        holds = {str(k): int(v) for k, v in holds.items()}
    has_side = "side_mode" in inspect.signature(sig.to_tradesim_signals).parameters
    source = "both"
    if "source_side=\"long_only\"" in rb or "source_side='long_only'" in rb:
        source = "long_only"
    live = pack in LIVE_PACKS
    if live:
        symbols = tuple(dict.fromkeys((*symbols, *LIVE_PACKS[pack]["live_symbols"])))
    return {
        "pack": pack,
        "symbols": tuple(symbols),
        "timeframes": tuple(timeframes),
        "holds": holds,
        "has_side_mode": has_side,
        "source_side": source,
        "live": live,
        "strategy_id": getattr(sig, "STRATEGY_ID", pack),
        "strategy_version": getattr(sig, "STRATEGY_VERSION", "0.1.0"),
        "build_signal_frame": sig.build_signal_frame,
        "to_tradesim_signals": sig.to_tradesim_signals,
    }


def list_packs() -> list[str]:
    names = []
    for p in sorted((ROOT / "strategies").iterdir()):
        if (p / "signals.py").is_file() and (p / "run_baseline.py").is_file():
            names.append(p.name)
    return names


def coverage_preflight() -> dict[str, float]:
    out: dict[str, float] = {}
    for symbol in COVERAGE_SYMBOLS:
        bars = _cached_ohlcv(symbol, COVERAGE_TF)
        touch = _cached_ohlcv(symbol, "1m")
        out[symbol] = touch_coverage_frac(bars, touch, COVERAGE_TF) if not bars.empty else 0.0
    return out


def run_pack(spec: dict, exec_mode: str) -> list[dict]:
    if spec["has_side_mode"]:
        rows = run_h0_matrix(
            strategy_id=spec["strategy_id"],
            strategy_version=spec["strategy_version"],
            symbols=spec["symbols"],
            timeframes=spec["timeframes"],
            holds=spec["holds"],
            build_signal_frame=spec["build_signal_frame"],
            to_tradesim_signals=spec["to_tradesim_signals"],
            source_side=spec["source_side"],
            test_opposite_mirror=spec["source_side"] == "long_only",
            exec_mode=exec_mode,  # type: ignore[arg-type]
            print_headline=False,
            require_touch_coverage=True,
        )
    else:
        rows = []
        for symbol in spec["symbols"]:
            for timeframe in spec["timeframes"]:
                rows.append(
                    run_one_side(
                        symbol=symbol,
                        timeframe=timeframe,
                        strategy_id=spec["strategy_id"],
                        strategy_version=spec["strategy_version"],
                        report_side="both",
                        side_mode="long",
                        build_signal_frame=spec["build_signal_frame"],
                        to_tradesim_signals=spec["to_tradesim_signals"],
                        max_hold_bars=int(spec["holds"].get(timeframe, 48)),
                        exec_mode=exec_mode,  # type: ignore[arg-type]
                        print_headline=False,
                        require_touch_coverage=True,
                    )
                )
    for r in rows:
        r["pack"] = spec["pack"]
        r["live"] = spec["live"]
        r["limit_offset"] = LIMIT_OFFSET_FROZEN if exec_mode == "exec021_limit" else None
    return rows


def _fmt(v: object, spec: str) -> str:
    if v is None:
        return "—"
    try:
        x = float(v)
    except (TypeError, ValueError):
        return str(v)
    if math.isnan(x) or math.isinf(x):
        return "nan"
    return format(x, spec)


def row_md(r: dict) -> str:
    return (
        f"| `{r.get('pack')}` | {r.get('exec_mode')} | {r.get('symbol')} | "
        f"{r.get('timeframe')} | {r.get('report_side')} | {r.get('n_trades', 0)} | "
        f"{_fmt(r.get('trades_per_month'), '.2f')} | {_fmt(r.get('profit_factor'), '.3f')} | "
        f"{_fmt(r.get('sharpe_ann'), '.3f')} | {_fmt(r.get('hac_sharpe_ann'), '.3f')} | "
        f"{_fmt(r.get('sortino_ann'), '.3f')} | {_fmt(r.get('win_rate'), '.1%')} | "
        f"{_fmt(r.get('expectancy'), '.4f')} | {_fmt(r.get('payoff_ratio'), '.3f')} | "
        f"{_fmt(r.get('net_pnl'), '.2f')} | {_fmt(r.get('max_drawdown'), '.2%')} | "
        f"{_fmt(r.get('exposure'), '.2%')} | {_fmt(r.get('total_fees'), '.2f')} | "
        f"{_fmt(r.get('entry_bar_exit_rate'), '.1%')} | {r.get('status')} |"
    )


HEADER = (
    "| Pack | Exec | Symbol | TF | Side | n | /mo | PF | Sharpe | HAC | Sortino | WR | "
    "Exp | Payoff | PnL | MDD | Exp% | Fees | same-bar | status |"
)
SEP = "|" + "|".join(["---"] * 20) + "|"


def write_markdown(rows: list[dict], coverage: dict[str, float]) -> str:
    live_rows = [r for r in rows if r.get("live")]
    other = [r for r in rows if not r.get("live")]
    cov_line = ", ".join(f"{k} 1h={v:.1%}" for k, v in coverage.items())
    lines = [
        "# EXEC-021 / 1-minute fill-clock fleet",
        "",
        f"**Maximum earned readiness:** `{H0_READINESS}`",
        f"**Evidence class:** `{H0_EVIDENCE_CLASS}` (full-history retest, not nested Out-Of-Sample)",
        "**Principal blocker:** Frozen Version 2.1 still requires nested outer exams; this file only corrects the simulator.",
        "",
        "Live in this project: `tsm_chandelier` (VPS94, Xxobster6, **market** entry, min size).",
        f"Post-Only offset (frozen): `{LIMIT_OFFSET_FROZEN}` (engine guide). Not searched.",
        f"1-minute touch coverage on 1-hour bars: {cov_line}. Gate `{MIN_TOUCH_COVERAGE:.0%}`.",
        "",
        "## Would I start a new min-size live test from this file?",
        "",
        "**No new pack.** Full-history Profit Factor is not an exam. The only live bot here is the already-authorized chandelier market-entry min-size experiment. `exec021_limit` on chandelier is a diagnostic for a Post-Only switch, not a live match.",
        "",
        "## Live pack",
        "",
        HEADER,
        SEP,
    ]
    if not live_rows:
        lines.append("| — | | | | | | | | | | | | | | | | | | | |")
    else:
        lines.extend(row_md(r) for r in live_rows)
    lines.extend(["", "## Not live (research packs)", "", HEADER, SEP])
    lines.extend(row_md(r) for r in other)
    skipped = ROOT / "strategies" / "tsm_liquidity_sweep"
    if skipped.is_dir() and not (skipped / "signals.py").is_file():
        lines.extend(
            [
                "",
                "## Packs not in this matrix",
                "",
                "`tsm_liquidity_sweep` has no `signals.py` (Smart Money Concepts confluence adapter). Abandoned family; not re-run here.",
            ]
        )
    return "\n".join(lines) + "\n"


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    import sqlite3

    db = research_db()
    con = sqlite3.connect(str(db))
    con.execute(
        "CREATE INDEX IF NOT EXISTS idx_ohlcv_sym_tf "
        "ON market_ohlcv(source, symbol, timeframe, is_complete, ts_ms)"
    )
    con.commit()
    con.close()
    coverage = coverage_preflight()
    print("1m coverage on 1h", coverage, flush=True)
    weak = {k: v for k, v in coverage.items() if k in ("BTCUSDT", "ETHUSDT") and v < MIN_TOUCH_COVERAGE}
    if weak:
        print(
            "REFUSING fleet: BTC/ETH 1-minute coverage is below the gate. "
            "Run research/backfill_1m_ohlcv.py first.",
            flush=True,
        )
        (OUT_DIR / "coverage_preflight.json").write_text(
            json.dumps({"coverage": coverage, "refused": True}, indent=2),
            encoding="utf-8",
        )
        raise SystemExit(2)

    done: list[dict] = []
    if CHECKPOINT.exists():
        done = json.loads(CHECKPOINT.read_text(encoding="utf-8"))
    done_keys = {
        (d.get("pack"), d.get("exec_mode"))
        for d in done
        if d.get("status") not in {"error", "incomplete_1m"}
        and d.get("pack")
        and d.get("exec_mode")
    }
    packs = list_packs()
    print("packs", len(packs), "limit_offset", LIMIT_OFFSET_FROZEN, flush=True)
    for pack in packs:
        try:
            spec = discover_pack(pack)
        except Exception:
            print("DISCOVER FAIL", pack, traceback.format_exc(), flush=True)
            done.append(
                {
                    "pack": pack,
                    "status": "error",
                    "live": pack in LIVE_PACKS,
                    "error": traceback.format_exc()[-1500:],
                }
            )
            CHECKPOINT.write_text(json.dumps(done, indent=2, default=str), encoding="utf-8")
            continue
        for exec_mode in ("taker_market", "exec021_limit"):
            if (pack, exec_mode) in done_keys:
                print("skip", pack, exec_mode, flush=True)
                continue
            print("RUN", pack, exec_mode, spec["symbols"], spec["timeframes"], flush=True)
            try:
                rows = run_pack(spec, exec_mode)
            except Exception:
                print("RUN FAIL", pack, exec_mode, traceback.format_exc(), flush=True)
                done.append(
                    {
                        "pack": pack,
                        "exec_mode": exec_mode,
                        "status": "error",
                        "live": spec["live"],
                        "error": traceback.format_exc()[-1500:],
                    }
                )
                CHECKPOINT.write_text(json.dumps(done, indent=2, default=str), encoding="utf-8")
                continue
            done.extend(rows)
            done_keys.add((pack, exec_mode))
            CHECKPOINT.write_text(json.dumps(done, indent=2, default=str), encoding="utf-8")
            for r in rows:
                print(
                    f"  {r.get('symbol')} {r.get('timeframe')} {r.get('report_side')} "
                    f"n={r.get('n_trades')} /mo={r.get('trades_per_month')} "
                    f"PF={r.get('profit_factor')} status={r.get('status')}",
                    flush=True,
                )
            md = OUT_DIR / "FLEET_RESULT.md"
            md.write_text(write_markdown(done, coverage), encoding="utf-8")
    final = OUT_DIR / "fleet_results.json"
    final.write_text(json.dumps(done, indent=2, default=str), encoding="utf-8")
    md = OUT_DIR / "FLEET_RESULT.md"
    md.write_text(write_markdown(done, coverage), encoding="utf-8")
    print("Wrote", final, md, flush=True)


if __name__ == "__main__":
    main()
