#!/usr/bin/env python3
"""Finplot: live bot vs backtest entries/exits on the same chart (two colors)."""
from __future__ import annotations

import json
import sqlite3
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tradesim.ensure_source import prefer_botsgeneral_tradesim

prefer_botsgeneral_tradesim()

from engine.data_loader import load_ohlcv, research_db
from engine.tradesim_adapter import PROJECT_STARTING_EQUITY_USDT, df_to_barseries
from strategies.tsm_chandelier.signals import build_signal_frame, to_tradesim_signals
from tradesim import run_backtest

try:
    import finplot as fplt
except ImportError as e:  # pragma: no cover
    raise SystemExit("finplot is required: pip install finplot") from e

OUT = ROOT / "artifacts" / "reports" / "tsm_chandelier"
LIVE_DB = OUT / "live_vps94_tsm_chandelier_live.sqlite"

# Distinct colors on one candle chart
COLOR_LIVE = "#00E5FF"  # cyan
COLOR_BT = "#FF8C00"  # dark orange
COLOR_LIVE_OPEN = "#7FDBFF"
COLOR_BT_OPEN = "#FFB347"


@dataclass
class PlotTrade:
    label: str
    side: str  # long|short
    entry_ts_ms: int
    entry_price: float
    exit_ts_ms: int | None
    exit_price: float | None
    source: str  # live|backtest


def utc(ms: int | None) -> str | None:
    if ms is None:
        return None
    return datetime.fromtimestamp(int(ms) / 1000, timezone.utc).isoformat()


def load_live_trades(path: Path) -> list[PlotTrade]:
    con = sqlite3.connect(str(path))
    con.row_factory = sqlite3.Row
    out: list[PlotTrade] = []
    for r in con.execute("select * from closed_trades"):
        # closed PnL side is the closing order side; infer position from planned entry
        side = "short"  # chandelier live shorts so far; refine from planned prices
        entry = float(r["avg_entry_price"] or 0)
        stop = float(r["planned_stop"] or 0)
        if stop and entry and stop < entry:
            side = "long"
        elif stop and entry and stop > entry:
            side = "short"
        out.append(
            PlotTrade(
                label=f"LIVE {r['symbol']}",
                side=side,
                entry_ts_ms=int(r["planned_entry_ts_ms"] or r["created_ms"]),
                entry_price=entry,
                exit_ts_ms=int(r["updated_ms"]) if r["updated_ms"] else None,
                exit_price=float(r["avg_exit_price"]) if r["avg_exit_price"] is not None else None,
                source="live",
            )
        )
    for r in con.execute("select * from open_trades"):
        out.append(
            PlotTrade(
                label=f"LIVE {r['symbol']} OPEN",
                side=str(r["side"]),
                entry_ts_ms=int(r["entry_ts_ms"]),
                entry_price=float(r["entry_price"]),
                exit_ts_ms=None,
                exit_price=None,
                source="live",
            )
        )
    con.close()
    return out


def resim_trades(symbol: str, entry_ts_ms: int) -> list[PlotTrade]:
    db = research_db()
    bars = load_ohlcv(db, symbol, "1h")
    start = entry_ts_ms - 200 * 3_600_000
    end = max(entry_ts_ms + 80 * 3_600_000, int(datetime.now(timezone.utc).timestamp() * 1000))
    bars = bars[(bars["ts_ms"] >= start) & (bars["ts_ms"] < end)].copy()
    if bars.empty:
        return []
    touch = load_ohlcv(db, symbol, "1m", start_ms=entry_ts_ms - 3_600_000, end_ms=end)
    feat = build_signal_frame(bars)
    sigs = to_tradesim_signals(feat, symbol, max_hold_bars=36)
    sig_ts = entry_ts_ms - 3_600_000
    sigs = [s for s in sigs if int(s.ts_ms) == sig_ts]
    if not sigs:
        return []
    bundle = run_backtest(
        strategy_id=f"plot_{symbol.lower()}",
        strategy_version="0.1.0",
        bars=df_to_barseries(feat, "1h", symbol),
        symbol=symbol,
        signals=sigs,
        touch_bars=df_to_barseries(touch, "1m", symbol) if not touch.empty else None,
        starting_equity=PROJECT_STARTING_EQUITY_USDT,
        plot=False,
        print_headline=False,
        store_path=None,
    )
    out: list[PlotTrade] = []
    for t in getattr(bundle.result, "trades", ()) or ():
        out.append(
            PlotTrade(
                label=f"BT {symbol}",
                side="long" if int(t.side) > 0 else "short",
                entry_ts_ms=int(t.entry_ts_ms),
                entry_price=float(t.entry_price),
                exit_ts_ms=int(t.exit_ts_ms) if t.exit_ts_ms else None,
                exit_price=float(t.exit_price) if t.exit_price else None,
                source="backtest",
            )
        )
    return out


def bars_for_symbol(symbol: str, *, pad_hours: int = 36) -> pd.DataFrame:
    live = load_live_trades(LIVE_DB)
    times = [t.entry_ts_ms for t in live if symbol in t.label]
    times += [t.exit_ts_ms for t in live if symbol in t.label and t.exit_ts_ms]
    if not times:
        # default window around deploy
        times = [int(datetime(2026, 8, 10, tzinfo=timezone.utc).timestamp() * 1000)]
    lo = min(times) - pad_hours * 3_600_000
    hi = max(times) + pad_hours * 3_600_000
    now = int(datetime.now(timezone.utc).timestamp() * 1000)
    hi = max(hi, now)
    df = load_ohlcv(research_db(), symbol, "1h")
    df = df[(df["ts_ms"] >= lo) & (df["ts_ms"] <= hi)].copy()
    df["time"] = pd.to_datetime(df["ts_ms"], unit="ms", utc=True)
    return df.reset_index(drop=True)


def _nearest_i(ts_ms: int, index: pd.DatetimeIndex) -> int:
    t = pd.Timestamp(ts_ms, unit="ms", tz="UTC")
    # exact or previous bar
    pos = index.get_indexer([t], method="pad")[0]
    if pos < 0:
        pos = index.get_indexer([t], method="backfill")[0]
    return int(max(0, min(pos, len(index) - 1)))


def _overlay_trade(ax, index: pd.DatetimeIndex, trade: PlotTrade, *, color: str, width: int = 3) -> None:
    i0 = _nearest_i(trade.entry_ts_ms, index)
    entry = float(trade.entry_price)
    if trade.exit_ts_ms is not None and trade.exit_price is not None:
        i1 = _nearest_i(trade.exit_ts_ms, index)
        if i1 == i0 and len(index) > 1:
            i1 = min(i0 + 1, len(index) - 1)
        exit_px = float(trade.exit_price)
        fplt.add_line((i0, entry), (i1, exit_px), color=color, width=width, style="-", ax=ax)
        fplt.plot([index[i1]], [exit_px], ax=ax, color=color, style="x", width=3, legend=None)
    else:
        # open trade: horizontal stub forward a few bars
        i1 = min(i0 + 4, len(index) - 1)
        fplt.add_line((i0, entry), (i1, entry), color=color, width=width, style="--", ax=ax)
    marker = "v" if trade.side == "short" else "^"
    fplt.plot([index[i0]], [entry], ax=ax, color=color, style=marker, width=3, legend=None)


def plot_symbol(symbol: str, ax, live_trades: list[PlotTrade], bt_trades: list[PlotTrade]) -> dict:
    df = bars_for_symbol(symbol)
    if df.empty:
        fplt.add_legend(f"{symbol}: no candles", ax=ax)
        return {"symbol": symbol, "bars": 0}
    candles = df.set_index("time")[["open", "close", "high", "low"]]
    fplt.candlestick_ochl(candles, ax=ax)
    index = candles.index

    live_sym = [t for t in live_trades if symbol in t.label]
    bt_sym = [t for t in bt_trades if t.label.endswith(symbol) or symbol in t.label]

    for t in bt_sym:
        _overlay_trade(ax, index, t, color=COLOR_BT if t.exit_ts_ms else COLOR_BT_OPEN, width=3)
    for t in live_sym:
        _overlay_trade(ax, index, t, color=COLOR_LIVE if t.exit_ts_ms else COLOR_LIVE_OPEN, width=3)

    fplt.add_legend(
        f"{symbol}  |  LIVE={COLOR_LIVE} (o/^/v + solid)  |  BACKTEST={COLOR_BT}  |  "
        f"live_n={len(live_sym)} bt_n={len(bt_sym)}",
        ax=ax,
    )
    # price labels
    for t in live_sym + bt_sym:
        i = _nearest_i(t.entry_ts_ms, index)
        tag = "L" if t.source == "live" else "B"
        fplt.add_text(
            (i, float(t.entry_price)),
            f"{tag} entry {t.entry_price:g}",
            color=COLOR_LIVE if t.source == "live" else COLOR_BT,
            ax=ax,
        )
        if t.exit_ts_ms and t.exit_price:
            j = _nearest_i(t.exit_ts_ms, index)
            fplt.add_text(
                (j, float(t.exit_price)),
                f"{tag} exit {t.exit_price:g}",
                color=COLOR_LIVE if t.source == "live" else COLOR_BT,
                ax=ax,
            )
    return {
        "symbol": symbol,
        "bars": len(df),
        "live": [t.__dict__ | {"entry_utc": utc(t.entry_ts_ms), "exit_utc": utc(t.exit_ts_ms)} for t in live_sym],
        "backtest": [
            t.__dict__ | {"entry_utc": utc(t.entry_ts_ms), "exit_utc": utc(t.exit_ts_ms)} for t in bt_sym
        ],
    }


def main() -> None:
    if not LIVE_DB.exists():
        raise SystemExit(f"missing live db: {LIVE_DB}")

    # dark background for readability
    fplt.foreground = "#D0D0D0"
    fplt.background = "#1E1E1E"
    fplt.odd_plot_background = "#1E1E1E"
    fplt.candle_bull_color = "#26A69A"
    fplt.candle_bear_color = "#EF5350"
    fplt.candle_bull_body_color = "#26A69A"
    fplt.candle_bear_body_color = "#EF5350"

    live = load_live_trades(LIVE_DB)
    symbols = sorted({t.label.split()[1] for t in live})
    if not symbols:
        raise SystemExit("no live trades to plot")

    bt: list[PlotTrade] = []
    for t in live:
        # one resim per live entry timestamp/symbol
        sym = t.label.split()[1]
        if any(b.label.endswith(sym) and b.entry_ts_ms == t.entry_ts_ms for b in bt):
            continue
        bt.extend(resim_trades(sym, t.entry_ts_ms))

    axes = fplt.create_plot(
        "tsm_chandelier live (cyan) vs backtest (orange)",
        rows=len(symbols),
        maximize=True,
    )
    if len(symbols) == 1:
        axes = [axes]

    summary = []
    for ax, sym in zip(axes, symbols):
        summary.append(plot_symbol(sym, ax, live, bt))

    meta_path = OUT / "live_vs_backtest_finplot_meta.json"
    meta_path.write_text(
        json.dumps(
            {
                "generated_utc": datetime.now(timezone.utc).isoformat(),
                "colors": {"live": COLOR_LIVE, "backtest": COLOR_BT},
                "symbols": summary,
            },
            indent=2,
            default=str,
        ),
        encoding="utf-8",
    )
    print("LIVE cyan", COLOR_LIVE, "| BACKTEST orange", COLOR_BT)
    print(json.dumps(summary, indent=2, default=str))
    print("meta", meta_path)
    fplt.show()


if __name__ == "__main__":
    main()
