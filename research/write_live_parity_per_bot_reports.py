#!/usr/bin/env python3
"""Split the combined live-parity JSON into per-bot and per-account reports."""
from __future__ import annotations

import json
from pathlib import Path

from live_parity_closeness import fmt_pct, score_account, score_bot

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "artifacts" / "reports" / "tsm_chandelier"
LATEST = OUT / "live_vs_bt_full_latest.json"

ACCOUNT = "Xxobster6"
PACK_ID = "tsm_chandelier_1h_btc_eth_sol_xxobster6_v1"
BOTS = {
    "BTCUSDT": {
        "unit": "tsm-chandelier@BTCUSDT",
        "freeze_role": "inside historical SHADOW_READY freeze (Bitcoin + Ethereum 1h)",
        "exploratory": False,
    },
    "ETHUSDT": {
        "unit": "tsm-chandelier@ETHUSDT",
        "freeze_role": "inside historical SHADOW_READY freeze (Bitcoin + Ethereum 1h)",
        "exploratory": False,
    },
    "SOLUSDT": {
        "unit": "tsm-chandelier@SOLUSDT",
        "freeze_role": "exploratory - not in the frozen Bitcoin + Ethereum claim",
        "exploratory": True,
    },
}


def _bt_trade(row: dict) -> dict:
    trades = (row.get("backtest") or {}).get("trades") or [{}]
    return trades[0] if trades else {}


def _closed_net(rows: list[dict]) -> float:
    return float(sum(float((r.get("live") or {}).get("closed_pnl") or 0) for r in rows))


def _bot_slice(full: dict, symbol: str) -> dict:
    meta = BOTS[symbol]
    closed = [r for r in full.get("closed_trades") or [] if r.get("symbol") == symbol]
    opened = [r for r in full.get("open_trades") or [] if r.get("symbol") == symbol]
    missed = [r for r in full.get("missed_or_extra_signals") or [] if r.get("symbol") == symbol]
    v = full.get("verdict") or {}
    candles = (full.get("candles") or {}).get(symbol) or {}
    indicators = (full.get("indicators") or {}).get(symbol) or {}
    signals = (full.get("signals_in_live_window") or {}).get(symbol) or []
    logic_ok = bool(indicators.get("research_vs_live_core_equal", True))
    candle_ok = bool((candles.get("vps_shared_vs_research") or {}).get("all_equal", True))

    def _levels_ok(rows: list[dict]) -> bool:
        for r in rows:
            sm = r.get("signal_match") or {}
            if sm.get("stop_match") is False or sm.get("target_match") is False:
                return False
            if "side_match" in sm and sm.get("side_match") is False:
                return False
        return True

    side_ok = _levels_ok(closed + opened)
    bot = {
        "generated_utc": full.get("generated_utc"),
        "account": ACCOUNT,
        "pack_id": PACK_ID,
        "bot_unit": meta["unit"],
        "symbol": symbol,
        "freeze_role": meta["freeze_role"],
        "exploratory": meta["exploratory"],
        "maximum_earned_readiness": "LIVE_STOP / RESEARCH_ONLY",
        "evidence_class": full.get("evidence_class"),
        "principal_blocker": full.get("principal_blocker"),
        "candles": candles,
        "indicators": indicators,
        "signals_in_live_window": signals,
        "closed_trades": closed,
        "open_trades": opened,
        "missed_or_extra_signals": missed,
        "closed_net_pnl_usdt": _closed_net(closed),
        "verdict": {
            "maximum_earned_readiness": "LIVE_STOP / RESEARCH_ONLY",
            "candles_match": candle_ok,
            "indicator_functions_match": logic_ok,
            "signal_side_stop_target_match": side_ok and logic_ok,
            "strategy_working_as_specified": bool(v.get("strategy_working_as_specified")) and side_ok,
            "material_logic_bug": bool(v.get("material_logic_bug")) and not side_ok,
            "closed_trade_count": len(closed),
            "open_trade_count": len(opened),
            "n_live_window_signals": len(signals),
            "closed_net_pnl_usdt": _closed_net(closed),
        },
        "notes_on_models": full.get("notes_on_models"),
    }
    bot["closeness"] = score_bot(bot)
    bot["verdict"]["closeness"] = bot["closeness"]
    return bot


def _account_slice(full: dict, bots: dict[str, dict]) -> dict:
    closed_n = sum(int((b.get("verdict") or {}).get("closed_trade_count") or 0) for b in bots.values())
    open_n = sum(int((b.get("verdict") or {}).get("open_trade_count") or 0) for b in bots.values())
    net = sum(float((b.get("verdict") or {}).get("closed_net_pnl_usdt") or 0) for b in bots.values())
    return {
        "generated_utc": full.get("generated_utc"),
        "account": ACCOUNT,
        "pack_id": PACK_ID,
        "bots": [BOTS[s]["unit"] for s in BOTS],
        "symbols": list(BOTS),
        "maximum_earned_readiness": "LIVE_STOP / RESEARCH_ONLY",
        "evidence_class": full.get("evidence_class"),
        "principal_blocker": full.get("principal_blocker"),
        "historical_freeze": (full.get("verdict") or {}).get("historical_freeze"),
        "closed_trade_count": closed_n,
        "open_trade_count": open_n,
        "closed_net_pnl_usdt": net,
        "per_bot_net_pnl_usdt": {
            s: (bots[s].get("verdict") or {}).get("closed_net_pnl_usdt") for s in BOTS
        },
        "closeness": score_account([bots[s].get("closeness") or {} for s in BOTS]),
        "per_bot_closeness": {s: bots[s].get("closeness") for s in BOTS},
        "strategy_working_as_specified": all(
            (bots[s].get("verdict") or {}).get("strategy_working_as_specified") for s in BOTS
        ),
        "material_logic_bug": any((bots[s].get("verdict") or {}).get("material_logic_bug") for s in BOTS),
        "bot_report_paths": {
            s: str(OUT / "by_bot" / f"{ACCOUNT}_{s}.json") for s in BOTS
        },
    }


def _fmt_px(x) -> str:
    if x is None:
        return "—"
    v = float(x)
    if abs(v) >= 1000:
        return f"{v:,.1f}"
    if abs(v) >= 10:
        return f"{v:.2f}"
    return f"{v:.4f}"


def _md_closeness_block(c: dict | None, *, heading: str = "## Closeness (live vs backtest)") -> list[str]:
    c = c or {}
    return [
        heading,
        "",
        "| Aspect | Score | What it measures |",
        "|---|---|---|",
        f"| Candles | **{fmt_pct(c.get('candles_pct'))}** | Overlapping 1-hour Open-High-Low-Close equal |",
        f"| Calculations | **{fmt_pct(c.get('calculations_pct'))}** | Average True Range / Exponential Moving Average / stop / target |",
        f"| Signals | **{fmt_pct(c.get('signals_pct'))}** | Live-window signals filled, still open, or valid skip |",
        f"| Entries / exits | **{fmt_pct(c.get('entries_exits_pct'))}** | Same side, bar, stop, target, exit reason |",
        f"| Fill prices | {fmt_pct(c.get('fill_price_pct'))} | Live vs backtest fill (designed slip allowed, not a bug) |",
        "",
    ]


def _md_bot(bot: dict) -> str:
    v = bot["verdict"]
    lines = [
        f"# Live parity — {bot['bot_unit']}",
        "",
        f"Account: **{bot['account']}**  ",
        f"Pack: `{bot['pack_id']}`  ",
        f"Symbol: **{bot['symbol']}**  ",
        f"Freeze role: {bot['freeze_role']}",
        "",
        f"Maximum earned readiness: **{bot['maximum_earned_readiness']}**  ",
        f"Evidence class: {bot['evidence_class']}  ",
        f"Generated: {bot['generated_utc']}",
        "",
        f"Principal blocker: {bot['principal_blocker']}",
        "",
        *_md_closeness_block(bot.get("closeness")),
        "## Verdict",
        "",
        f"- Candles match: {v['candles_match']}",
        f"- Indicator functions match: {v['indicator_functions_match']}",
        f"- Signal side / stop / target match: {v['signal_side_stop_target_match']}",
        f"- Strategy working as specified: {v['strategy_working_as_specified']}",
        f"- Closed trades: {v['closed_trade_count']}  |  open: {v['open_trade_count']}  |  live-window signals: {v['n_live_window_signals']}",
        f"- Closed net profit and loss (USDT): **{float(v['closed_net_pnl_usdt']):+.4f}**",
        "",
        "## Closed trades",
        "",
    ]
    if not bot["closed_trades"]:
        lines.append("None.")
    else:
        lines.append("| Side | Live net | Live exit | Entry → exit (live) | Backtest entry → exit | 1-minute first touch | Levels match |")
        lines.append("|---|---|---|---|---|---|---|")
        for r in bot["closed_trades"]:
            live = r.get("live") or {}
            bt = _bt_trade(r)
            sm = r.get("signal_match") or {}
            touch = (r.get("one_m_path") or {}).get("first_touch")
            match = "yes" if sm.get("side_match") and sm.get("stop_match") and sm.get("target_match") else "NO"
            lines.append(
                "| {side} | {pnl:+.4f} | {ex} | {le} → {lx} | {be} → {bx} ({br}) | {touch} | {match} |".format(
                    side=live.get("side"),
                    pnl=float(live.get("closed_pnl") or 0),
                    ex=live.get("exit_type"),
                    le=_fmt_px(live.get("entry_px")),
                    lx=_fmt_px(live.get("exit_px")),
                    be=_fmt_px(bt.get("entry_price")),
                    bx=_fmt_px(bt.get("exit_price")),
                    br=bt.get("exit_reason") or "—",
                    touch=touch or "—",
                    match=match,
                )
            )
    lines += ["", "## Open trades", ""]
    if not bot["open_trades"]:
        lines.append("None.")
    else:
        lines.append("| Side | Entry UTC | Live entry | Stop | Target | 1-minute first touch | Backtest |")
        lines.append("|---|---|---|---|---|---|---|")
        for r in bot["open_trades"]:
            live = r.get("live") or {}
            touch = (r.get("one_m_path") or {}).get("first_touch")
            still = (r.get("backtest") or {}).get("still_open")
            lines.append(
                "| {side} | {utc} | {px} | {sl} | {tp} | {touch} | still_open={still} |".format(
                    side=live.get("side"),
                    utc=(live.get("entry_utc") or "")[:19],
                    px=_fmt_px(live.get("entry_px")),
                    sl=_fmt_px(live.get("planned_stop")),
                    tp=_fmt_px(live.get("planned_target")),
                    touch=touch or "none",
                    still=still,
                )
            )
    lines += ["", "## Live-window signals", ""]
    if not bot["signals_in_live_window"]:
        lines.append("None.")
    else:
        lines.append("| Entry UTC | Side | Stop | Target | Live action |")
        lines.append("|---|---|---|---|---|")
        missed = {(m.get("entry_utc"), m.get("side")): m for m in bot["missed_or_extra_signals"]}
        closed_hours = {((r.get("live") or {}).get("entry_utc") or "")[:16] for r in bot["closed_trades"]}
        open_hours = {((r.get("live") or {}).get("entry_utc") or "")[:16] for r in bot["open_trades"]}
        for s in bot["signals_in_live_window"]:
            hour = (s.get("entry_utc") or "")[:16]
            m = next(
                (
                    x
                    for x in bot["missed_or_extra_signals"]
                    if (x.get("entry_utc") or "")[:16] == hour and x.get("side") == s.get("side")
                ),
                None,
            )
            if m:
                action = f"skipped ({m.get('reason')})"
            elif hour in open_hours:
                action = "open"
            elif hour in closed_hours:
                action = "filled (closed)"
            else:
                action = "see live database"
            lines.append(
                f"| {hour} | {s.get('side')} | {_fmt_px(s.get('stop'))} | {_fmt_px(s.get('target'))} | {action} |"
            )
    lines += [
        "",
        "Designed fill gaps (not bugs): Bybit market entry vs Binance next-open + 0.05% slip; live Stop Loss / Take Profit market slip vs backtest fill at planned price.",
        "",
    ]
    return "\n".join(lines)


def _md_account(acc: dict) -> str:
    lines = [
        f"# Live parity — account {acc['account']}",
        "",
        f"Pack: `{acc['pack_id']}`  ",
        f"Bots: {', '.join(f'`{u}`' for u in acc['bots'])}  ",
        f"Generated: {acc['generated_utc']}",
        "",
        f"Maximum earned readiness: **{acc['maximum_earned_readiness']}**  ",
        f"Evidence class: {acc['evidence_class']}",
        "",
        f"Principal blocker: {acc['principal_blocker']}",
        "",
        f"Historical freeze: {acc['historical_freeze']}",
        "",
        *_md_closeness_block(acc.get("closeness"), heading="## Closeness (account mean)"),
        "## Rollup",
        "",
        f"- Closed trades: {acc['closed_trade_count']}  |  open: {acc['open_trade_count']}",
        f"- Closed net profit and loss (USDT): **{float(acc['closed_net_pnl_usdt']):+.4f}**",
        f"- Strategy working as specified: {acc['strategy_working_as_specified']}",
        f"- Material logic bug: {acc['material_logic_bug']}",
        "",
        "## Per bot",
        "",
        "| Bot | Symbol | Candles | Calculations | Signals | Entries/exits | Fill prices | Closed net USDT |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for s in acc["symbols"]:
        unit = BOTS[s]["unit"]
        net = float((acc.get("per_bot_net_pnl_usdt") or {}).get(s) or 0)
        c = (acc.get("per_bot_closeness") or {}).get(s) or {}
        lines.append(
            "| `{unit}` | {s} | {candles} | {calc} | {sig} | {ex} | {fill} | {net:+.4f} |".format(
                unit=unit,
                s=s,
                candles=fmt_pct(c.get("candles_pct")),
                calc=fmt_pct(c.get("calculations_pct")),
                sig=fmt_pct(c.get("signals_pct")),
                ex=fmt_pct(c.get("entries_exits_pct")),
                fill=fmt_pct(c.get("fill_price_pct")),
                net=net,
            )
        )
    lines += ["", "Solana is exploratory and is not inside the frozen Bitcoin + Ethereum Shadow-ready claim.", ""]
    return "\n".join(lines)


def write_reports(full: dict, out_dir: Path | None = None) -> dict[str, Path]:
    out_dir = out_dir or OUT
    by_bot = out_dir / "by_bot"
    by_acc = out_dir / "by_account"
    by_bot.mkdir(parents=True, exist_ok=True)
    by_acc.mkdir(parents=True, exist_ok=True)
    written: dict[str, Path] = {}
    bots: dict[str, dict] = {}
    for sym in BOTS:
        bot = _bot_slice(full, sym)
        bots[sym] = bot
        jp = by_bot / f"{ACCOUNT}_{sym}.json"
        mp = by_bot / f"{ACCOUNT}_{sym}.md"
        jp.write_text(json.dumps(bot, indent=2, default=str), encoding="utf-8")
        mp.write_text(_md_bot(bot), encoding="utf-8")
        written[f"bot_{sym}_json"] = jp
        written[f"bot_{sym}_md"] = mp
    acc = _account_slice(full, bots)
    aj = by_acc / f"{ACCOUNT}.json"
    am = by_acc / f"{ACCOUNT}.md"
    aj.write_text(json.dumps(acc, indent=2, default=str), encoding="utf-8")
    am.write_text(_md_account(acc), encoding="utf-8")
    written["account_json"] = aj
    written["account_md"] = am
    return written


def write_from_latest(path: Path | None = None) -> dict[str, Path]:
    src = path or LATEST
    if not src.exists():
        raise SystemExit(f"missing {src}")
    full = json.loads(src.read_text(encoding="utf-8"))
    written = write_reports(full)
    for p in written.values():
        print("WROTE", p)
    return written


if __name__ == "__main__":
    write_from_latest()
