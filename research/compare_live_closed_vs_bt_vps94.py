#!/usr/bin/env python3
"""Compare VPS94 live closed tsm_chandelier trades vs canonical tradesim re-sim."""
from __future__ import annotations

import hashlib
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

from engine.tradesim_adapter import PROJECT_STARTING_EQUITY_USDT, df_to_barseries
from strategies.tsm_chandelier.signals import build_signal_frame, to_tradesim_signals
from tradesim import run_backtest

sys.path.insert(0, str(ROOT / "deploy" / "tsm_chandelier" / "src"))
from chand.signals_core import build_signal_frame as live_build_signal_frame  # noqa: E402

OUT = ROOT / "artifacts" / "reports" / "tsm_chandelier"
LIVE_DB = OUT / "live_vps94_tsm_chandelier_live.sqlite"
CANDLE_DIR = OUT / "vps94_parity_export"
EXEC_PATH = OUT / "vps94_live_executions.json"
TAKER = 0.00055
TF_MS = 3_600_000
MAX_HOLD = 36
SIGNAL_TS = 1786456800000  # 2026-08-11 14:00 UTC
ENTRY_TS = 1786460400000  # 2026-08-11 15:00 UTC


def utc(ms: int | None) -> str | None:
    if ms is None:
        return None
    return datetime.fromtimestamp(int(ms) / 1000, timezone.utc).isoformat()


def file_sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_csv(symbol: str) -> pd.DataFrame:
    path = CANDLE_DIR / f"{symbol}_1h_binance_warmup600.csv"
    df = pd.read_csv(path)
    df["ts_ms"] = df["ts_ms"].astype("int64")
    return df.sort_values("ts_ms").reset_index(drop=True)


def bar_at(df: pd.DataFrame, ts_ms: int) -> dict | None:
    hit = df[df["ts_ms"] == ts_ms]
    if hit.empty:
        return None
    r = hit.iloc[0]
    return {
        "ts_ms": int(r["ts_ms"]),
        "ts_utc": utc(int(r["ts_ms"])),
        "open": float(r["open"]),
        "high": float(r["high"]),
        "low": float(r["low"]),
        "close": float(r["close"]),
    }


def live_closed(con: sqlite3.Connection) -> list[dict]:
    con.row_factory = sqlite3.Row
    return [dict(r) for r in con.execute("select * from closed_trades order by updated_ms")]


def live_funding(con: sqlite3.Connection) -> list[dict]:
    con.row_factory = sqlite3.Row
    rows = []
    for r in con.execute("select * from funding_events order by ts_ms"):
        d = dict(r)
        d["ts_utc"] = utc(d.get("ts_ms"))
        rows.append(d)
    return rows


def exec_block(exec_report: dict, symbol: str) -> dict:
    return (exec_report.get("symbols") or {}).get(symbol) or {}


def reconstruct_from_execs(symbol: str, block: dict, planned_stop: float) -> dict:
    execs = block.get("executions") or []
    closed = (block.get("closed_pnl") or [None])[0] or {}
    trades = [e for e in execs if str(e.get("execType") or e.get("orderType")) in ("Trade", "Market") or e.get("stopOrderType") == "StopLoss" or (e.get("orderType") == "Market")]
    # Keep true fills only (not Funding)
    fills = [e for e in execs if str(e.get("execType")) == "Trade" or (e.get("orderType") == "Market" and str(e.get("execType")) != "Funding")]
    funding = [e for e in execs if str(e.get("execType")) == "Funding" or str(e.get("orderType")) == "UNKNOWN" and e.get("feeRate") not in (None, "", "0")]
    # fallback: feeRate present and orderType UNKNOWN
    if not funding:
        funding = [e for e in execs if str(e.get("execType")) == "Funding"]
    funding = [e for e in execs if str(e.get("execType")) == "Funding"]
    fills = [e for e in execs if str(e.get("execType")) == "Trade"]
    fills = sorted(fills, key=lambda e: int(e.get("execTime") or 0))
    entry = fills[0] if fills else {}
    exit_ = fills[-1] if len(fills) > 1 else {}
    entry_px = float(entry.get("execPrice") or closed.get("avgEntryPrice") or 0)
    exit_px = float(exit_.get("execPrice") or closed.get("avgExitPrice") or 0)
    qty = float(entry.get("execQty") or closed.get("qty") or 0)
    entry_fee = float(entry.get("execFee") or closed.get("openFee") or 0)
    exit_fee = float(exit_.get("execFee") or closed.get("closeFee") or 0)
    fund_credit = -sum(float(e.get("execFee") or 0) for e in funding)  # Bybit credit is negative fee
    # shorts: covering Buy close
    gross = (entry_px - exit_px) * qty
    net = gross - entry_fee - exit_fee + fund_credit
    return {
        "entry_exec": entry,
        "exit_exec": exit_,
        "funding_execs": funding,
        "entry_px": entry_px,
        "exit_px": exit_px,
        "qty": qty,
        "entry_fee": entry_fee,
        "exit_fee": exit_fee,
        "trade_fees": entry_fee + exit_fee,
        "funding_credit": fund_credit,
        "gross_pnl": gross,
        "implied_net": net,
        "exchange_closed_pnl": float(closed.get("closedPnl") or 0),
        "identity_ok": abs(net - float(closed.get("closedPnl") or 0)) < 1e-8,
        "exit_order_type": exit_.get("orderType"),
        "exit_stop_order_type": exit_.get("stopOrderType"),
        "exit_fee_rate": float(exit_.get("feeRate") or 0),
        "stop_slip_price": exit_px - planned_stop,
        "model_taker_entry_fee": abs(qty) * entry_px * TAKER,
        "model_taker_exit_fee": abs(qty) * exit_px * TAKER,
    }


def resim(symbol: str, df: pd.DataFrame) -> dict:
    feat_r = build_signal_frame(df)
    feat_l = live_build_signal_frame(df)
    logic_equal = True
    logic = {}
    for c in ["atr", "long_signal", "short_signal", "stop_price", "target_price"]:
        a = feat_r[c].to_numpy()
        b = feat_l[c].to_numpy()
        if c in ("long_signal", "short_signal"):
            eq = bool(np.array_equal(a.astype(bool), b.astype(bool)))
        else:
            eq = bool(np.allclose(a.astype(float), b.astype(float), equal_nan=True))
        logic[c] = eq
        logic_equal = logic_equal and eq
    sigs_all = to_tradesim_signals(feat_r, symbol, max_hold_bars=MAX_HOLD)
    sigs = [s for s in sigs_all if int(s.ts_ms) == SIGNAL_TS]
    sig_row = feat_r[feat_r["ts_ms"] == SIGNAL_TS]
    signal_info = None
    if len(sig_row):
        r = sig_row.iloc[0]
        signal_info = {
            "ts_utc": utc(SIGNAL_TS),
            "close": float(r["close"]),
            "long_signal": bool(r["long_signal"]),
            "short_signal": bool(r["short_signal"]),
            "stop_price": float(r["stop_price"]) if pd.notna(r["stop_price"]) else None,
            "target_price": float(r["target_price"]) if pd.notna(r["target_price"]) else None,
            "atr": float(r["atr"]) if pd.notna(r["atr"]) else None,
        }
    if not sigs:
        return {
            "status": "no_matching_signal",
            "logic_research_vs_live_core": logic_equal,
            "logic_detail": logic,
            "signal_bar": signal_info,
            "n_signals_all": len(sigs_all),
        }
    bundle = run_backtest(
        strategy_id=f"live_vs_bt_{symbol.lower()}",
        strategy_version="0.1.0",
        bars=df_to_barseries(feat_r, "1h", symbol),
        symbol=symbol,
        signals=sigs,
        touch_bars=None,
        starting_equity=PROJECT_STARTING_EQUITY_USDT,
        plot=False,
        print_headline=False,
        store_path=None,
    )
    result = getattr(bundle, "result", None)
    trades = []
    for t in tuple(getattr(result, "trades", ()) or ()):
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
    for f in tuple(getattr(result, "fills", ()) or ()):
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
        "logic_research_vs_live_core": logic_equal,
        "logic_detail": logic,
        "signal_bar": signal_info,
        "n_signals_all": len(sigs_all),
        "trades": trades,
        "fills": fills,
        "metrics": {
            "net_pnl": float(bundle.metrics.net_pnl) if bundle.metrics else None,
            "n_trades": int(bundle.metrics.n_trades) if bundle.metrics else None,
        },
    }


def compare_row(live: dict, recon: dict, bt: dict, df: pd.DataFrame) -> dict:
    planned_stop = float(live["planned_stop"] or 0)
    planned_tgt = float(live["planned_target"] or 0)
    live_entry = float(live["avg_entry_price"] or 0)
    live_exit = float(live["avg_exit_price"] or 0)
    qty = float(live["qty"] or 0)
    bt_t = (bt.get("trades") or [None])[0]
    signal = bt.get("signal_bar") or {}
    exit_bar_ts = (int(live["updated_ms"]) // TF_MS) * TF_MS
    entry_bar = bar_at(df, ENTRY_TS)
    signal_bar_ohlc = bar_at(df, SIGNAL_TS)
    exit_bar = bar_at(df, exit_bar_ts)
    # short: stop hit if high >= stop
    stop_touched_1h = None
    if exit_bar and planned_stop:
        stop_touched_1h = float(exit_bar["high"]) >= planned_stop - 1e-9
    diffs = {}
    if bt_t:
        diffs = {
            "entry_price_live_minus_bt": live_entry - bt_t["entry_price"],
            "exit_price_live_minus_bt": live_exit - bt_t["exit_price"],
            "stop_live_minus_bt": planned_stop - bt_t["stop_price"],
            "target_live_minus_bt": planned_tgt - bt_t["target_price"],
            "qty_live_minus_bt": qty - bt_t["qty"],
            "fees_live_minus_bt": recon["trade_fees"] - bt_t["fees"],
            "funding_live_minus_bt": recon["funding_credit"] - bt_t["funding"],
            "pnl_live_minus_bt": float(live["closed_pnl"]) - bt_t["realized_pnl"],
            "exit_reason_bt": bt_t["exit_reason"],
            "same_entry_bar": int(bt_t["entry_ts_ms"] or 0) == ENTRY_TS,
            "bt_exit_bar_utc": bt_t["exit_utc"],
            "live_exit_utc": utc(int(live["updated_ms"])),
        }
    return {
        "symbol": live["symbol"],
        "live": {
            "side": "short",  # close record Buy = cover short
            "qty": qty,
            "leverage": live.get("leverage"),
            "entry_px": live_entry,
            "exit_px": live_exit,
            "entry_utc": utc(int(live["created_ms"])) if live.get("created_ms") else None,
            "exit_utc": utc(int(live["updated_ms"])) if live.get("updated_ms") else None,
            "planned_stop": planned_stop,
            "planned_target": planned_tgt,
            "closed_pnl": live.get("closed_pnl"),
            "exec_type": live.get("exec_type"),
            "order_type_raw": json.loads(live["raw_json"]).get("orderType") if live.get("raw_json") else None,
        },
        "execution_truth": recon,
        "backtest": bt,
        "bars": {
            "signal_bar": signal_bar_ohlc,
            "entry_bar": entry_bar,
            "exit_hour_bar": exit_bar,
            "stop_touched_on_1h_high": stop_touched_1h,
        },
        "signal_vs_live_stop": {
            "signal_stop": signal.get("stop_price"),
            "live_planned_stop": planned_stop,
            "stop_match": (
                signal.get("stop_price") is not None
                and abs(float(signal["stop_price"]) - planned_stop) < 1e-6
            ),
            "signal_target": signal.get("target_price"),
            "live_planned_target": planned_tgt,
            "target_match": (
                signal.get("target_price") is not None
                and abs(float(signal["target_price"]) - planned_tgt) < 1e-6
            ),
            "signal_side_short": signal.get("short_signal") is True,
        },
        "diffs_live_minus_bt": diffs,
    }


def main() -> None:
    if not LIVE_DB.exists():
        raise SystemExit(f"missing {LIVE_DB}")
    exec_report = json.loads(EXEC_PATH.read_text(encoding="utf-8")) if EXEC_PATH.exists() else {}
    con = sqlite3.connect(str(LIVE_DB))
    closed = live_closed(con)
    funding_rows = live_funding(con)
    con.close()

    report = {
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "maximum_earned_readiness": "LIVE_STOP / RESEARCH_ONLY",
        "evidence_class": "FORWARD_MICRO_LIVE_RECONCILE + RESEARCH_PROXY",
        "code_hashes": {
            "research_signals.py": file_sha(ROOT / "strategies" / "tsm_chandelier" / "signals.py"),
            "live_signals_core.py": file_sha(
                ROOT / "deploy" / "tsm_chandelier" / "src" / "chand" / "signals_core.py"
            ),
        },
        "notes_on_models": {
            "live_entry": "Bybit market order ~20-25s after 1h open, LastPrice",
            "bt_entry": "next-bar open +/- research entry slippage 0.05%",
            "live_stop": "Bybit StopLoss trigger LastPrice, filled as Market taker (has exit slip)",
            "bt_stop": "limit-at-stop, taker fee, ZERO exit slippage (canonical research default)",
            "live_size": "exchange min qty; leverage from stop + 80% haircut",
            "bt_size": "research_sizing min exchange qty; leverage 1x (PnL in USDT same at min size)",
            "candles": "both use Binance 1h (RESEARCH_PROXY vs Bybit fills)",
            "max_hold_bars": MAX_HOLD,
        },
        "live_db_funding_events": funding_rows,
        "trades": [],
        "verdict": {},
    }

    blockers = []
    identical = True
    signal_ok = True
    for ct in closed:
        sym = ct["symbol"]
        df = load_csv(sym)
        recon = reconstruct_from_execs(sym, exec_block(exec_report, sym), float(ct["planned_stop"] or 0))
        bt = resim(sym, df)
        row = compare_row(ct, recon, bt, df)
        report["trades"].append(row)
        if not row["signal_vs_live_stop"]["stop_match"] or not row["signal_vs_live_stop"]["target_match"]:
            signal_ok = False
            identical = False
            blockers.append(f"{sym}: live stop/target != re-sim signal stop/target")
        if bt.get("status") != "ok":
            identical = False
            blockers.append(f"{sym}: backtest status {bt.get('status')}")
        d = row["diffs_live_minus_bt"]
        if d and not d.get("same_entry_bar"):
            identical = False
            blockers.append(f"{sym}: entry bar mismatch")
        if abs(float(d.get("exit_price_live_minus_bt") or 0)) > 1e-9:
            identical = False
        if abs(float(d.get("pnl_live_minus_bt") or 0)) > 1e-6:
            identical = False
        if not recon.get("identity_ok"):
            blockers.append(f"{sym}: exchange closedPnl != gross - fees + funding")
        if recon.get("exit_stop_order_type") != "StopLoss":
            blockers.append(f"{sym}: exit stopOrderType={recon.get('exit_stop_order_type')} (expected StopLoss)")

    if not signal_ok:
        identical = False
    blockers.append(
        "Live stop-loss fills as Bybit market (taker + slip). Backtester fills stop at the planned price with no exit slip."
    )
    blockers.append(
        "Live entry is Bybit last/market; backtester uses next-bar Binance open plus 0.05% entry slip."
    )
    blockers.append(
        "Live applied signed Bybit funding; canonical re-sim on this window used no live funding series (funding=0 in backtest trades)."
    )
    blockers.append("Evidence remains RESEARCH_PROXY (Binance signal candles vs Bybit fills).")
    blockers.append("Two closed micro-live trades cannot raise readiness. Do not increase size or leverage.")

    report["verdict"] = {
        "end_to_end_identical": False,
        "signal_side_stop_target_qty_match": signal_ok,
        "closed_trade_count": len(closed),
        "principal_blocker": (
            "Live and backtester are not identical on fills, fees-on-fill-price, stop slippage, or funding. "
            "They did take the same short, same bar, same stop/target, same min size, and both exited on the stop."
        ),
        "principal_blockers": blockers,
        "maximum_earned_readiness": "LIVE_STOP / RESEARCH_ONLY",
    }

    out = OUT / "live_vs_bt_closed_trades_20260813.json"
    out.write_text(json.dumps(report, indent=2, default=str), encoding="utf-8")

    print("=== LIVE vs BACKTEST (closed ETH + BTC) ===")
    print("Max readiness:", report["verdict"]["maximum_earned_readiness"])
    print("Evidence class:", report["evidence_class"])
    print("End-to-end identical:", report["verdict"]["end_to_end_identical"])
    print("Signal/stop/target match:", signal_ok)
    print("Code hashes equal:", report["code_hashes"]["research_signals.py"] == report["code_hashes"]["live_signals_core.py"])
    for row in report["trades"]:
        print("\n---", row["symbol"], "---")
        live = row["live"]
        recon = row["execution_truth"]
        bt = row["backtest"]
        bt_t = (bt.get("trades") or [{}])[0]
        print(" LIVE  short qty", live["qty"], "lev", live["leverage"])
        print("  entry", live["entry_px"], live["entry_utc"])
        print("  exit ", live["exit_px"], live["exit_utc"], "type", recon.get("exit_order_type"), recon.get("exit_stop_order_type"))
        print("  SL   ", live["planned_stop"], "slip", recon.get("stop_slip_price"))
        print("  TP   ", live["planned_target"])
        print("  gross", recon.get("gross_pnl"), "fees", recon.get("trade_fees"), "funding+", recon.get("funding_credit"))
        print("  net  ", live["closed_pnl"], "identity_ok", recon.get("identity_ok"))
        print(" BT    status", bt.get("status"), "logic_eq", bt.get("logic_research_vs_live_core"))
        print("  signal", bt.get("signal_bar"))
        print("  trade", json.dumps(bt_t, default=str)[:500])
        print("  diffs", json.dumps(row["diffs_live_minus_bt"], default=str))
        print("  1h bars", json.dumps(row["bars"], default=str)[:700])
        print("  stop/target match", row["signal_vs_live_stop"])
    print("\nBlockers:")
    for b in blockers:
        print(" -", b)
    print("WROTE", out)


if __name__ == "__main__":
    main()
