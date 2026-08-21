#!/usr/bin/env python3
"""Reconcile VPS94 live closed trades vs local re-sim (exits, fees, funding, MTM)."""
from __future__ import annotations

import json
import sqlite3
import sys
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

OUT = ROOT / "artifacts" / "reports" / "tsm_chandelier"
LIVE_DB_DEFAULT = OUT / "live_vps94_tsm_chandelier_live.sqlite"
TAKER = 0.00055


def utc(ms: int | None) -> str | None:
    if ms is None:
        return None
    return datetime.fromtimestamp(int(ms) / 1000, timezone.utc).isoformat()


def load_live(path: Path) -> dict:
    con = sqlite3.connect(str(path))
    con.row_factory = sqlite3.Row
    out = {
        "closed": [dict(r) for r in con.execute("select * from closed_trades order by updated_ms")],
        "open": [dict(r) for r in con.execute("select * from open_trades")],
        "funding": [dict(r) for r in con.execute("select * from funding_events order by ts_ms")],
        "equity": [
            dict(r)
            for r in con.execute(
                """
                select ts_ms, ts_utc, symbol, wallet_balance, total_equity, available,
                       position_size, position_side, unrealised_pnl, mark_price
                from equity_snapshots order by ts_ms
                """
            )
        ],
        "entry_events": [
            dict(r)
            for r in con.execute(
                "select ts_utc, symbol, kind, detail_json from events where kind in ('entry_filled','entry_timing','position_closed')"
            )
        ],
    }
    con.close()
    return out


def approx_taker_fees(entry: float, exit_: float, qty: float) -> dict:
    entry_fee = abs(qty) * entry * TAKER
    exit_fee = abs(qty) * exit_ * TAKER
    return {
        "entry_fee": entry_fee,
        "exit_fee": exit_fee,
        "total_fee": entry_fee + exit_fee,
        "rate": TAKER,
        "note": "Bybit USDT perp Fee = Qty * ExecutedPrice * Rate; baseline taker 0.055%",
    }


def resim_symbol(symbol: str, entry_ts_ms: int) -> dict:
    db = research_db()
    bars = load_ohlcv(db, symbol, "1h")
    if bars.empty:
        return {"status": "no_bars"}
    # include warmup before entry signal (prior bar)
    start = entry_ts_ms - 200 * 3_600_000
    end = entry_ts_ms + 80 * 3_600_000
    bars = bars[(bars["ts_ms"] >= start) & (bars["ts_ms"] <= end)].copy()
    touch = load_ohlcv(db, symbol, "1m", start_ms=entry_ts_ms - 3_600_000, end_ms=end)
    feat = build_signal_frame(bars)
    sigs = to_tradesim_signals(feat, symbol, max_hold_bars=36)
    # keep only the live entry signal bar (signal on previous hour)
    sig_ts = entry_ts_ms - 3_600_000
    sigs = [s for s in sigs if int(s.ts_ms) == sig_ts]
    if not sigs:
        return {"status": "no_matching_signal", "signal_ts_ms": sig_ts}
    bundle = run_backtest(
        strategy_id=f"reconcile_{symbol.lower()}",
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
    trades = []
    result = getattr(bundle, "result", None)
    raw_trades = tuple(getattr(result, "trades", ()) or ()) if result is not None else ()
    for t in raw_trades:
        trades.append(
            {
                "side": int(getattr(t, "side", 0) or 0),
                "entry_ts_ms": getattr(t, "entry_ts_ms", None),
                "entry_utc": utc(getattr(t, "entry_ts_ms", None)),
                "exit_ts_ms": getattr(t, "exit_ts_ms", None),
                "exit_utc": utc(getattr(t, "exit_ts_ms", None)),
                "entry_price": float(getattr(t, "entry_price", 0) or 0),
                "exit_price": float(getattr(t, "exit_price", 0) or 0),
                "qty": float(getattr(t, "qty", 0) or 0),
                "fees": float(getattr(t, "fees", 0) or 0),
                "funding": float(getattr(t, "funding", 0) or 0),
                "slippage_cost": float(getattr(t, "slippage_cost", 0) or 0),
                "gross_pnl": float(getattr(t, "gross_pnl", 0) or 0),
                "realized_pnl": float(getattr(t, "realized_pnl", 0) or 0),
                "exit_reason": getattr(t, "exit_reason", None),
                "stop_price": float(getattr(t, "stop_price", 0) or 0),
                "target_price": float(getattr(t, "target_price", 0) or 0),
            }
        )
    fills = []
    for f in tuple(getattr(result, "fills", ()) or ()) if result is not None else ():
        fills.append(
            {
                "ts_ms": getattr(f, "ts_ms", None),
                "ts_utc": utc(getattr(f, "ts_ms", None)),
                "role": getattr(f, "role", None),
                "side": getattr(f, "side", None),
                "qty": float(getattr(f, "qty", 0) or 0),
                "price": float(getattr(f, "price", 0) or 0),
                "fee": float(getattr(f, "fee", 0) or 0),
                "fee_rate": float(getattr(f, "fee_rate", 0) or 0),
                "slippage_cost": float(getattr(f, "slippage_cost", 0) or 0),
            }
        )
    return {
        "status": "ok",
        "n_signals": 1,
        "n_trades": len(trades),
        "trades": trades,
        "fills": fills,
        "metrics": {
            "net_pnl": float(bundle.metrics.net_pnl) if bundle.metrics else None,
            "n_trades": int(bundle.metrics.n_trades) if bundle.metrics else None,
        },
        "compare_notes": [
            "Resim entry uses next-bar open +/- entry slippage model; live uses Bybit market fill.",
            "Resim stop exit uses planned stop (no exit slip when limit-touch assumed); live SL was market-triggered.",
            "1m touch series may be absent locally — exit bar then comes from 1h path.",
        ],
    }


def equity_path(rows: list[dict], symbol: str) -> dict:
    sub = [r for r in rows if r["symbol"] == symbol]
    if not sub:
        return {"n": 0}
    eq = np.array([float(r["total_equity"] or 0) for r in sub], dtype=float)
    return {
        "n": len(sub),
        "first_utc": sub[0]["ts_utc"],
        "last_utc": sub[-1]["ts_utc"],
        "equity_start": float(eq[0]),
        "equity_end": float(eq[-1]),
        "equity_min": float(eq.min()),
        "equity_max": float(eq.max()),
        "delta": float(eq[-1] - eq[0]),
    }


def main() -> None:
    live_path = Path(sys.argv[1]) if len(sys.argv) > 1 else LIVE_DB_DEFAULT
    if not live_path.exists():
        raise SystemExit(f"missing live db {live_path}")
    live = load_live(live_path)
    report = {
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "live_db": str(live_path),
        "maximum_earned_readiness": "LIVE_STOP / RESEARCH_ONLY",
        "evidence_class": "FORWARD_MICRO_LIVE_RECONCILE",
        "open_trades": [
            {
                "symbol": t["symbol"],
                "side": t["side"],
                "entry_utc": utc(t["entry_ts_ms"]),
                "entry_price": t["entry_price"],
                "stop": t["stop_price"],
                "target": t["target_price"],
            }
            for t in live["open"]
        ],
        "closed_reconcile": [],
        "funding": [],
        "equity_mtm": {},
        "verdict": {},
    }

    for f in live["funding"]:
        report["funding"].append(
            {
                "symbol": f["symbol"],
                "ts_utc": utc(f.get("ts_ms")),
                "funding": f.get("funding"),
                "cash_flow": f.get("cash_flow"),
                "size": f.get("size"),
                "side": f.get("side"),
            }
        )

    for sym in sorted({t["symbol"] for t in live["closed"] + live["open"] + live["funding"]}):
        report["equity_mtm"][sym] = equity_path(live["equity"], sym)

    blockers = []
    for ct in live["closed"]:
        entry = float(ct["avg_entry_price"] or 0)
        exit_ = float(ct["avg_exit_price"] or 0)
        qty = float(ct["qty"] or 0)
        planned_stop = float(ct["planned_stop"] or 0)
        fees = approx_taker_fees(entry, exit_, qty)
        # exchange closedPnl is typically net of fees for Bybit closed-pnl endpoint
        gross = (entry - exit_) * qty if str(ct.get("side")).lower() in ("buy", "sell") else None
        # For a short, exchange side on close record is Buy (cover). PnL = (entry-exit)*qty
        if str(ct.get("side")) == "Buy":  # covering short
            gross_pnl = (entry - exit_) * qty
        else:
            gross_pnl = (exit_ - entry) * qty
        stop_slip = exit_ - planned_stop if planned_stop else None
        resim = resim_symbol(ct["symbol"], int(ct["planned_entry_ts_ms"] or 0))
        # Optional execution truth injected via sidecar JSON (from VPS Bybit executions).
        exec_path = OUT / "live_exec_fees_sidecar.json"
        exec_truth = {}
        if exec_path.exists():
            try:
                exec_truth = json.loads(exec_path.read_text(encoding="utf-8")).get(ct["symbol"], {})
            except Exception:
                exec_truth = {}
        row = {
            "symbol": ct["symbol"],
            "live": {
                "entry_utc": utc(ct.get("planned_entry_ts_ms")),
                "exit_utc": utc(ct.get("updated_ms")),
                "side_close_record": ct.get("side"),
                "qty": qty,
                "entry": entry,
                "exit": exit_,
                "planned_stop": planned_stop,
                "planned_target": ct.get("planned_target"),
                "closed_pnl_exchange": ct.get("closed_pnl"),
                "exec_type": ct.get("exec_type"),
                "stop_exit_slip": stop_slip,
            },
            "fee_model_taker": fees,
            "execution_truth": exec_truth,
            "accounting": {
                "gross_pnl_from_prices": gross_pnl,
                "gross_minus_model_fees": gross_pnl - fees["total_fee"],
                "exchange_closed_pnl": ct.get("closed_pnl"),
                "exchange_vs_gross_minus_fees": (
                    float(ct["closed_pnl"]) - (gross_pnl - fees["total_fee"])
                    if ct.get("closed_pnl") is not None
                    else None
                ),
            },
            "resim": resim,
        }
        fund_rows = []
        for f in report["funding"]:
            if f["symbol"] != ct["symbol"] or not f.get("ts_utc"):
                continue
            ts = int(datetime.fromisoformat(f["ts_utc"].replace("Z", "+00:00")).timestamp() * 1000)
            if int(ct.get("planned_entry_ts_ms") or 0) <= ts <= int(ct.get("updated_ms") or 0):
                fund_rows.append(f)
        row["funding_while_open"] = fund_rows
        report["closed_reconcile"].append(row)

        if abs(float(stop_slip or 0)) > abs(planned_stop) * 0.002:
            blockers.append(
                f"{ct['symbol']}: stop exit slipped {stop_slip} vs planned {planned_stop}"
            )
        if resim.get("status") != "ok":
            blockers.append(f"{ct['symbol']}: resim status {resim.get('status')}")

    if live["open"]:
        blockers.append(
            "BTCUSDT (or other) still open — full exit/funding/MTM parity incomplete until flat."
        )
    if any((f.get("cash_flow") in (0, 0.0, None)) and f.get("funding") for f in report["funding"]):
        blockers.append(
            "funding_events.cash_flow is 0 while funding!=0 — verify Bybit funding field mapping before trusting wallet funding parity."
        )
    blockers.append("Evidence remains RESEARCH_PROXY (Binance signal candles vs Bybit fills).")
    blockers.append("Do not raise size/leverage on this thin forward sample.")

    report["verdict"] = {
        "signal_stop_target_parity": "PASS (prior)",
        "closed_trade_count": len(live["closed"]),
        "open_trade_count": len(live["open"]),
        "full_live_backtest_identity": False,
        "principal_blockers": blockers,
        "maximum_earned_readiness": "LIVE_STOP / RESEARCH_ONLY",
    }

    path = OUT / "live_closed_reconcile_vps94.json"
    path.write_text(json.dumps(report, indent=2, default=str), encoding="utf-8")
    print("closed", len(live["closed"]), "open", len(live["open"]))
    for row in report["closed_reconcile"]:
        print(
            row["symbol"],
            "exit",
            row["live"]["exit"],
            "stop",
            row["live"]["planned_stop"],
            "slip",
            row["live"]["stop_exit_slip"],
            "ex_pnl",
            row["live"]["closed_pnl_exchange"],
            "model_net",
            row["accounting"]["gross_minus_model_fees"],
            "resim",
            row["resim"].get("status"),
            row["resim"].get("trades"),
        )
    print("funding", report["funding"])
    print("equity", json.dumps(report["equity_mtm"]))
    print("WROTE", path)


if __name__ == "__main__":
    main()
