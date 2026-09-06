"""Live vs backtest closeness scores (percent) for live-parity sitreps.

Logic match is scored separately from fill-price closeness. Designed
slippage (Bybit market vs Binance next-open) must not look like a bug.
"""
from __future__ import annotations

from typing import Any

VALID_SIGNAL_SKIPS = frozenset(
    {
        "in_position",
        "qty0",
        "below_min_qty",
        "min_qty",
        "min_notional",
        "stale",
        "stale_entry",
    }
)

ASPECT_KEYS = (
    "candles_pct",
    "calculations_pct",
    "signals_pct",
    "entries_exits_pct",
    "fill_price_pct",
)


def fmt_pct(value: float | None) -> str:
    if value is None:
        return "n/a"
    if abs(value - round(value)) < 0.05:
        return f"{int(round(value))}%"
    return f"{value:.1f}%"


def _mean01(values: list[float]) -> float | None:
    if not values:
        return None
    return 100.0 * (sum(values) / len(values))


def candles_pct(candles: dict[str, Any] | None) -> float | None:
    block = (candles or {}).get("vps_shared_vs_research") or {}
    n = int(block.get("n_overlap") or 0)
    if n <= 0:
        if "all_equal" in block:
            return 100.0 if block.get("all_equal") else 0.0
        return None
    diffs = block.get("n_diff") or {}
    if diffs:
        worst = max(int(v) for v in diffs.values())
        return max(0.0, 100.0 * (1.0 - worst / n))
    return 100.0 if block.get("all_equal") else 0.0


def calculations_pct(indicators: dict[str, Any] | None) -> float | None:
    ind = indicators or {}
    detail = ind.get("detail") or {}
    if detail:
        vals = [1.0 if bool(v) else 0.0 for v in detail.values()]
        return _mean01(vals)
    if "research_vs_live_core_equal" in ind:
        return 100.0 if ind.get("research_vs_live_core_equal") else 0.0
    return None


def _hour(ts: str | None) -> str:
    return (ts or "")[:16]


def _signal_accounted(sig: dict[str, Any], bot: dict[str, Any]) -> bool:
    hour = _hour(sig.get("entry_utc"))
    side = sig.get("side")
    for row in list(bot.get("closed_trades") or []) + list(bot.get("open_trades") or []):
        live = row.get("live") or {}
        if _hour(live.get("entry_utc")) == hour and live.get("side") == side:
            return True
    for missed in bot.get("missed_or_extra_signals") or []:
        if _hour(missed.get("entry_utc")) == hour and missed.get("side") == side:
            return (missed.get("reason") or "") in VALID_SIGNAL_SKIPS
    return False


def signals_pct(bot: dict[str, Any]) -> float | None:
    signals = bot.get("signals_in_live_window") or []
    if not signals:
        return None
    ok = sum(1 for s in signals if _signal_accounted(s, bot))
    return 100.0 * ok / len(signals)


def _exit_reason_aligned(live_exit: str | None, bt_reason: str | None) -> bool | None:
    live = (live_exit or "").lower()
    bt = (bt_reason or "").lower()
    if not live or not bt:
        return None
    if live == bt:
        return True
    pairs = (
        ("stoploss", "stop"),
        ("takeprofit", "target"),
        ("timeout", "time"),
        ("timeout", "max_hold"),
        ("timeout", "maxhold"),
    )
    for a, b in pairs:
        if a in live and b in bt:
            return True
        if b in live and a in bt:
            return True
    return False


def _bt_trade(row: dict[str, Any]) -> dict[str, Any]:
    trades = (row.get("backtest") or {}).get("trades") or [{}]
    return trades[0] if trades else {}


def _rel_close(live_px: Any, bt_px: Any) -> float | None:
    if live_px is None or bt_px is None:
        return None
    b = float(bt_px)
    if abs(b) < 1e-12:
        return None
    return max(0.0, 1.0 - abs(float(live_px) - b) / abs(b))


def _trade_logic01(row: dict[str, Any], *, open_only: bool) -> list[float]:
    sm = row.get("signal_match") or {}
    diffs = row.get("diffs_live_minus_bt") or {}
    checks: list[float] = []
    for key in ("side_match", "stop_match", "target_match"):
        if key in sm:
            checks.append(1.0 if sm.get(key) else 0.0)
    if "same_entry_bar" in sm:
        checks.append(1.0 if sm.get("same_entry_bar") else 0.0)
    elif "same_entry_bar" in diffs:
        checks.append(1.0 if diffs.get("same_entry_bar") else 0.0)
    if open_only:
        return checks
    live = row.get("live") or {}
    bt = _bt_trade(row)
    aligned = _exit_reason_aligned(
        live.get("exit_type"),
        bt.get("exit_reason") or diffs.get("bt_exit_reason"),
    )
    if aligned is not None:
        checks.append(1.0 if aligned else 0.0)
    touch = (row.get("one_m_path") or {}).get("first_touch")
    if touch and live.get("exit_type"):
        checks.append(1.0 if str(touch).lower() == str(live.get("exit_type")).lower() else 0.0)
    return checks


def _trade_fill01(row: dict[str, Any], *, open_only: bool) -> list[float]:
    live = row.get("live") or {}
    bt = _bt_trade(row)
    parts: list[float] = []
    entry = _rel_close(live.get("entry_px"), bt.get("entry_price"))
    if entry is not None:
        parts.append(entry)
    if not open_only:
        ex = _rel_close(live.get("exit_px"), bt.get("exit_price"))
        if ex is not None:
            parts.append(ex)
    return parts


def entries_exits_pct(bot: dict[str, Any]) -> tuple[float | None, float | None]:
    logic: list[float] = []
    fills: list[float] = []
    for row in bot.get("closed_trades") or []:
        c = _trade_logic01(row, open_only=False)
        if c:
            logic.append(sum(c) / len(c))
        f = _trade_fill01(row, open_only=False)
        if f:
            fills.append(sum(f) / len(f))
    for row in bot.get("open_trades") or []:
        c = _trade_logic01(row, open_only=True)
        if c:
            logic.append(sum(c) / len(c))
        f = _trade_fill01(row, open_only=True)
        if f:
            fills.append(sum(f) / len(f))
    return _mean01(logic), _mean01(fills)


def score_bot(bot: dict[str, Any]) -> dict[str, Any]:
    logic, fill = entries_exits_pct(bot)
    candles = candles_pct(bot.get("candles"))
    calc = calculations_pct(bot.get("indicators"))
    sig = signals_pct(bot)
    present = [x for x in (candles, calc, sig, logic) if x is not None]
    overall = sum(present) / len(present) if present else None
    n_overlap = int(((bot.get("candles") or {}).get("vps_shared_vs_research") or {}).get("n_overlap") or 0)
    n_sig = len(bot.get("signals_in_live_window") or [])
    return {
        "candles_pct": candles,
        "calculations_pct": calc,
        "signals_pct": sig,
        "entries_exits_pct": logic,
        "fill_price_pct": fill,
        "overall_pct": overall,
        "notes": {
            "candles": f"{n_overlap} overlapping 1h bars" if n_overlap else "no overlapping bars",
            "calculations": "Average True Range / Exponential Moving Average / stop / target functions",
            "signals": f"{n_sig} live-window signals (filled, open, or valid skip)",
            "entries_exits": "side, bar, stop, target, exit reason, 1-minute first touch",
            "fill_price": "relative live vs backtest fill prices (designed slip allowed)",
        },
    }


def score_account(bot_scores: list[dict[str, Any]]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for key in ASPECT_KEYS + ("overall_pct",):
        vals = [float(s[key]) for s in bot_scores if s.get(key) is not None]
        out[key] = (sum(vals) / len(vals)) if vals else None
    return out


def format_glimpse_table(
    rows: list[dict[str, Any]],
    *,
    title: str,
) -> str:
    """Plain-text table: one row per bot, then optional ACCOUNT mean."""
    headers = (
        "bot",
        "candles",
        "calculations",
        "signals",
        "entries/exits",
        "fill prices",
    )
    body: list[tuple[str, str, str, str, str, str]] = []
    for row in rows:
        body.append(
            (
                str(row.get("label") or ""),
                fmt_pct(row.get("candles_pct")),
                fmt_pct(row.get("calculations_pct")),
                fmt_pct(row.get("signals_pct")),
                fmt_pct(row.get("entries_exits_pct")),
                fmt_pct(row.get("fill_price_pct")),
            )
        )
    widths = [len(h) for h in headers]
    for line in body:
        for i, cell in enumerate(line):
            widths[i] = max(widths[i], len(cell))
    widths[0] = max(widths[0], 12)

    def _fmt(line: tuple[str, ...]) -> str:
        return "  ".join(cell.ljust(widths[i]) for i, cell in enumerate(line))

    out = [title, _fmt(headers), _fmt(tuple("-" * w for w in widths))]
    for line in body:
        out.append(_fmt(line))
    return "\n".join(out)
