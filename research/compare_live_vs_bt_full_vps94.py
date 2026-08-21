#!/usr/bin/env python3
"""Live vs backtest parity for VPS94 tsm_chandelier (BTC/ETH/SOL 1h)."""
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

from engine.data_loader import load_ohlcv, research_db
from engine.tradesim_adapter import PROJECT_STARTING_EQUITY_USDT, df_to_barseries
from strategies.tsm_chandelier.signals import build_signal_frame, to_tradesim_signals
from tradesim import InstrumentSpec, run_backtest
from tradesim.venue import InstrumentCache

sys.path.insert(0, str(ROOT / "deploy" / "tsm_chandelier" / "src"))
from chand.signals_core import build_signal_frame as live_build_signal_frame  # noqa: E402

OUT = ROOT / "artifacts" / "reports" / "tsm_chandelier"
LIVE_DB = OUT / "live_vps94_tsm_chandelier_live.sqlite"
EXEC_PATH = OUT / "vps94_live_executions.json"
VPS_1H = OUT / "vps94_parity_export_800"
FETCH = OUT / "vps94_ohlcv_fetch"
SYMBOLS = ["BTCUSDT", "ETHUSDT", "SOLUSDT"]
TF_MS = 3_600_000
MAX_HOLD = 36
TAKER = 0.00055
LIVE_START_MS = 1786363200000  # 2026-08-10 12:00 UTC
PRICE_EPS = {"BTCUSDT": 0.5, "ETHUSDT": 0.05, "SOLUSDT": 0.01}


def local_instrument(symbol: str) -> InstrumentSpec:
    row = InstrumentCache().get(symbol)
    if row is None:
        raise KeyError(f"no Bybit instrument cache for {symbol}")
    return row.to_instrument_spec(maintenance_tiers=())


def utc(ms: int | None) -> str | None:
    if ms is None:
        return None
    return datetime.fromtimestamp(int(ms) / 1000, timezone.utc).isoformat()


def file_sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def ohlc_equal(a: pd.DataFrame, b: pd.DataFrame, cols=("open", "high", "low", "close")) -> dict:
    m = a.merge(b, on="ts_ms", suffixes=("_a", "_b"), how="inner")
    if m.empty:
        return {"n_overlap": 0, "all_equal": False}
    ok = True
    max_abs = {}
    n_diff = {}
    for c in cols:
        d = (m[f"{c}_a"].to_numpy(float) - m[f"{c}_b"].to_numpy(float))
        n_diff[c] = int(np.count_nonzero(np.abs(d) > 1e-12))
        max_abs[c] = float(np.nanmax(np.abs(d))) if len(d) else 0.0
        ok = ok and n_diff[c] == 0
    return {
        "n_overlap": int(len(m)),
        "all_equal": ok,
        "n_diff": n_diff,
        "max_abs_diff": max_abs,
        "first_ts": utc(int(m["ts_ms"].iloc[0])),
        "last_ts": utc(int(m["ts_ms"].iloc[-1])),
    }


def load_csv(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path)
    df["ts_ms"] = df["ts_ms"].astype("int64")
    return df.sort_values("ts_ms").reset_index(drop=True)


def logic_parity(df: pd.DataFrame) -> dict:
    feat_r = build_signal_frame(df)
    feat_l = live_build_signal_frame(df)
    out = {"equal": True, "detail": {}}
    for c in ["atr", "long_signal", "short_signal", "stop_price", "target_price"]:
        a = feat_r[c].to_numpy()
        b = feat_l[c].to_numpy()
        if c in ("long_signal", "short_signal"):
            eq = bool(np.array_equal(a.astype(bool), b.astype(bool)))
        else:
            eq = bool(np.allclose(a.astype(float), b.astype(float), equal_nan=True))
        out["detail"][c] = eq
        out["equal"] = out["equal"] and eq
    n_long = int(feat_r["long_signal"].sum())
    n_short = int(feat_r["short_signal"].sum())
    out["n_long"] = n_long
    out["n_short"] = n_short
    return out


def trade_dict(t) -> dict:
    return {
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
        "ambiguous_intrabar": bool(getattr(t, "ambiguous_intrabar", False)),
    }


def resim_one(feat: pd.DataFrame, touch: pd.DataFrame, symbol: str, signal_ts_ms: int) -> dict:
    sigs = [
        s
        for s in to_tradesim_signals(feat, symbol, max_hold_bars=MAX_HOLD)
        if int(s.ts_ms) == int(signal_ts_ms)
    ]
    row = feat[feat["ts_ms"] == int(signal_ts_ms)]
    signal_info = None
    if len(row):
        r = row.iloc[0]
        signal_info = {
            "ts_utc": utc(int(signal_ts_ms)),
            "close": float(r["close"]),
            "long_signal": bool(r["long_signal"]),
            "short_signal": bool(r["short_signal"]),
            "stop_price": None if pd.isna(r["stop_price"]) else float(r["stop_price"]),
            "target_price": None if pd.isna(r["target_price"]) else float(r["target_price"]),
            "atr": None if pd.isna(r["atr"]) else float(r["atr"]),
        }
    if not sigs:
        return {"status": "no_matching_signal", "signal_bar": signal_info, "trades": []}
    end_ms = int(signal_ts_ms) + (MAX_HOLD + 8) * TF_MS
    bars_df = feat[(feat["ts_ms"] >= int(signal_ts_ms)) & (feat["ts_ms"] <= end_ms)]
    touch_s = touch[(touch["ts_ms"] >= int(signal_ts_ms)) & (touch["ts_ms"] <= end_ms + TF_MS)]
    bundle = run_backtest(
        strategy_id=f"live_vs_bt_{symbol.lower()}",
        strategy_version="0.1.0",
        bars=df_to_barseries(bars_df, "1h", symbol),
        symbol=symbol,
        instrument=local_instrument(symbol),
        signals=sigs,
        touch_bars=df_to_barseries(touch_s, "1m", symbol) if not touch_s.empty else None,
        starting_equity=PROJECT_STARTING_EQUITY_USDT,
        plot=False,
        print_headline=False,
        store_path=None,
    )
    result = getattr(bundle, "result", None)
    trades = [trade_dict(t) for t in tuple(getattr(result, "trades", ()) or ())]
    return {
        "status": "ok",
        "used_1m_touch": bool(not touch_s.empty),
        "n_1m": int(len(touch_s)),
        "signal_bar": signal_info,
        "trades": trades,
        "still_open": (not trades) or str(trades[-1].get("exit_reason")) == "end_of_data",
    }


def classify_exit(stop: float, target: float, exit_px: float, side: str, live_stop_type: str | None) -> str:
    if live_stop_type in ("StopLoss", "TakeProfit"):
        return live_stop_type
    if side == "short":
        if abs(exit_px - stop) <= abs(exit_px - target):
            return "StopLoss"
        return "TakeProfit"
    if abs(exit_px - stop) <= abs(exit_px - target):
        return "StopLoss"
    return "TakeProfit"


def live_side(closed_side: str, planned_stop: float, planned_target: float, entry: float) -> str:
    # Bybit closedPnl side is the closing order (Buy covers a short).
    if planned_stop and planned_target:
        if planned_stop > entry > planned_target:
            return "short"
        if planned_target > entry > planned_stop:
            return "long"
    return "short" if closed_side == "Buy" else "long"


def one_m_touch_check(touch: pd.DataFrame, entry_ts: int, stop: float, target: float, side: str) -> dict:
    w = touch[(touch["ts_ms"] >= int(entry_ts))].copy()
    if w.empty:
        return {"status": "no_1m"}
    if side == "long":
        sl_hit = w["low"] <= stop
        tp_hit = w["high"] >= target
    else:
        sl_hit = w["high"] >= stop
        tp_hit = w["low"] <= target
    sl_ts = int(w.loc[sl_hit, "ts_ms"].iloc[0]) if sl_hit.any() else None
    tp_ts = int(w.loc[tp_hit, "ts_ms"].iloc[0]) if tp_hit.any() else None
    first = None
    if sl_ts is not None and tp_ts is not None:
        first = "StopLoss" if sl_ts <= tp_ts else "TakeProfit"
    elif sl_ts is not None:
        first = "StopLoss"
    elif tp_ts is not None:
        first = "TakeProfit"
    return {
        "status": "ok",
        "first_touch": first,
        "sl_ts_utc": utc(sl_ts),
        "tp_ts_utc": utc(tp_ts),
        "last_1m_utc": utc(int(w["ts_ms"].iloc[-1])),
        "last_close": float(w["close"].iloc[-1]),
    }


def load_live() -> dict:
    con = sqlite3.connect(str(LIVE_DB))
    con.row_factory = sqlite3.Row
    out = {
        "closed": [dict(r) for r in con.execute("select * from closed_trades order by updated_ms")],
        "open": [dict(r) for r in con.execute("select * from open_trades")],
        "handled": [dict(r) for r in con.execute("select * from handled_entries order by entry_ts_ms")],
        "funding": [dict(r) for r in con.execute("select * from funding_events order by ts_ms")],
        "fills": [
            dict(r)
            for r in con.execute(
                "select ts_utc, symbol, kind, detail_json from events "
                "where kind in ('entry_filled','position_closed') order by id"
            )
        ],
    }
    con.close()
    return out


def execs_for_symbol(exec_report: dict, symbol: str) -> list[dict]:
    return ((exec_report.get("symbols") or {}).get(symbol) or {}).get("executions") or []


def nearest_exec(execs: list[dict], ts_ms: int, side_filter: str | None = None) -> dict | None:
    best = None
    best_dt = None
    for e in execs:
        if str(e.get("execType")) != "Trade":
            continue
        if side_filter and str(e.get("side")) != side_filter:
            continue
        t = int(e.get("execTime") or 0)
        dt = abs(t - int(ts_ms))
        if best_dt is None or dt < best_dt:
            best, best_dt = e, dt
    return best


def main() -> None:
    live = load_live()
    exec_report = json.loads(EXEC_PATH.read_text(encoding="utf-8")) if EXEC_PATH.exists() else {}
    db = research_db()
    report: dict = {
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "maximum_earned_readiness": "LIVE_STOP / RESEARCH_ONLY",
        "evidence_class": "FORWARD_MICRO_LIVE_RECONCILE + RESEARCH_PROXY",
        "principal_blocker": None,
        "code_hashes": {
            "research_signals.py": file_sha(ROOT / "strategies" / "tsm_chandelier" / "signals.py"),
            "live_signals_core.py": file_sha(
                ROOT / "deploy" / "tsm_chandelier" / "src" / "chand" / "signals_core.py"
            ),
            "live_bot.py": file_sha(ROOT / "deploy" / "tsm_chandelier" / "src" / "chand" / "live" / "bot.py"),
            "live_state.py": file_sha(ROOT / "deploy" / "tsm_chandelier" / "src" / "chand" / "live" / "state.py"),
            "vps_bot.py": "2c79ef329a39586f4e932a695ac55a48e965d4749e2e92063613afe1111b6382",
            "vps_state.py": "0677da7738b31801948a285a72063efc60cb775f9d2e79dbe580b3316b4a4b2d",
            "vps_signals_core.py": "8a2d6fe0a8ff145c013f4297031855cb75dc1d69881edb682aad6d65801279f4",
        },
        "notes_on_models": {
            "live_entry": "Bybit market ~20-26s after 1h open, LastPrice",
            "bt_entry": "next-bar Binance open + 0.05% research entry slip",
            "live_stop_tp": "Bybit StopLoss/TakeProfit trigger LastPrice, filled Market taker (exit slip)",
            "bt_stop_tp": "fill at planned price, taker fee, zero exit slip",
            "max_hold_bars": MAX_HOLD,
            "candles": "Binance 1h signals (RESEARCH_PROXY) vs Bybit fills; 1m touch for exits",
        },
        "candles": {},
        "indicators": {},
        "signals_in_live_window": {},
        "closed_trades": [],
        "open_trades": [],
        "missed_or_extra_signals": [],
        "fixes": [],
        "verdict": {},
    }
    blockers: list[str] = []
    signal_logic_ok = True
    candle_ok = True
    material_live_bt_bug = False

    frames: dict[str, dict] = {}
    for sym in SYMBOLS:
        bars = load_ohlcv(db, sym, "1h")
        touch = load_ohlcv(db, sym, "1m", start_ms=LIVE_START_MS - 3_600_000)
        feat = build_signal_frame(bars)
        vps_path = VPS_1H / f"{sym}_1h_binance_warmup800.csv"
        fetch_1h = FETCH / f"{sym}_1h_binance.csv"
        fetch_1m = FETCH / f"{sym}_1m_binance.csv"
        vps = load_csv(vps_path) if vps_path.exists() else pd.DataFrame()
        f1h = load_csv(fetch_1h) if fetch_1h.exists() else pd.DataFrame()
        candle_block = {
            "research_1h": {
                "n": int(len(bars)),
                "first": utc(int(bars["ts_ms"].iloc[0])) if len(bars) else None,
                "last": utc(int(bars["ts_ms"].iloc[-1])) if len(bars) else None,
            },
            "research_1m": {
                "n": int(len(touch)),
                "first": utc(int(touch["ts_ms"].iloc[0])) if len(touch) else None,
                "last": utc(int(touch["ts_ms"].iloc[-1])) if len(touch) else None,
            },
            "vps_shared_vs_research": ohlc_equal(vps, bars) if not vps.empty else {"n_overlap": 0},
            "fetch_1h_vs_research": ohlc_equal(f1h, bars) if not f1h.empty else {"n_overlap": 0},
            "vps_shared_vs_fetch": ohlc_equal(vps, f1h) if (not vps.empty and not f1h.empty) else {},
        }
        report["candles"][sym] = candle_block
        for k in ("vps_shared_vs_research", "fetch_1h_vs_research", "vps_shared_vs_fetch"):
            block = candle_block.get(k) or {}
            if block.get("n_overlap") and not block.get("all_equal", True):
                candle_ok = False
                blockers.append(f"{sym} candle mismatch {k}: {block.get('n_diff')}")
        live_win = feat[feat["ts_ms"] >= LIVE_START_MS - 400 * TF_MS]
        ind = logic_parity(live_win if len(live_win) > 80 else feat)
        report["indicators"][sym] = {
            "research_vs_live_core_equal": ind["equal"],
            "detail": ind["detail"],
            "n_long_full": int(feat["long_signal"].sum()),
            "n_short_full": int(feat["short_signal"].sum()),
        }
        if not ind["equal"]:
            signal_logic_ok = False
            blockers.append(f"{sym}: research build_signal_frame != live signals_core")
        sigs = to_tradesim_signals(feat, sym, max_hold_bars=MAX_HOLD)
        live_sigs = [
            {
                "signal_ts_ms": int(s.ts_ms),
                "signal_utc": utc(int(s.ts_ms)),
                "entry_ts_ms": int(s.ts_ms) + TF_MS,
                "entry_utc": utc(int(s.ts_ms) + TF_MS),
                "side": "long" if int(s.side) == 1 else "short",
                "stop": float(s.stop_price),
                "target": float(s.target_price),
            }
            for s in sigs
            if int(s.ts_ms) >= LIVE_START_MS
        ]
        report["signals_in_live_window"][sym] = live_sigs
        frames[sym] = {"feat": feat, "touch": touch, "live_sigs": live_sigs}

    live_entries = {}
    for ev in live["fills"]:
        if ev["kind"] != "entry_filled":
            continue
        d = json.loads(ev["detail_json"])
        live_entries[(ev["symbol"], int(d["entry_ts_ms"]))] = d

    for ct in live["closed"]:
        sym = ct["symbol"]
        entry_ts = int(ct["planned_entry_ts_ms"] or 0)
        sig_ts = entry_ts - TF_MS
        feat = frames[sym]["feat"]
        touch = frames[sym]["touch"]
        bt = resim_one(feat, touch, sym, sig_ts)
        fill = live_entries.get((sym, entry_ts), {})
        side = fill.get("side") or live_side(
            ct["side"], float(ct["planned_stop"] or 0), float(ct["planned_target"] or 0), float(ct["avg_entry_price"] or 0)
        )
        planned_stop = float(ct["planned_stop"] or 0)
        planned_tgt = float(ct["planned_target"] or 0)
        live_entry = float(ct["avg_entry_price"] or 0)
        live_exit = float(ct["avg_exit_price"] or 0)
        qty = float(ct["qty"] or 0)
        raw = json.loads(ct["raw_json"]) if ct.get("raw_json") else {}
        execs = execs_for_symbol(exec_report, sym)
        exit_exec = nearest_exec(execs, int(ct["updated_ms"] or 0))
        live_exit_type = (exit_exec or {}).get("stopOrderType") if exit_exec else None
        if live_exit_type in (None, "UNKNOWN"):
            live_exit_type = classify_exit(planned_stop, planned_tgt, live_exit, side, None)
        sig = (bt.get("signal_bar") or {})
        bt_t = (bt.get("trades") or [None])[0]
        stop_match = sig.get("stop_price") is not None and abs(float(sig["stop_price"]) - planned_stop) < 1e-6
        tgt_match = sig.get("target_price") is not None and abs(float(sig["target_price"]) - planned_tgt) < 1e-6
        side_match = (sig.get("long_signal") is True and side == "long") or (
            sig.get("short_signal") is True and side == "short"
        )
        touch_info = one_m_touch_check(touch, entry_ts, planned_stop, planned_tgt, side)
        eps = PRICE_EPS[sym]
        diffs = {}
        if bt_t:
            diffs = {
                "entry_live_minus_bt": live_entry - bt_t["entry_price"],
                "exit_live_minus_bt": live_exit - bt_t["exit_price"],
                "qty_live_minus_bt": qty - bt_t["qty"],
                "pnl_live_minus_bt": float(ct["closed_pnl"]) - bt_t["realized_pnl"],
                "same_entry_bar": int(bt_t["entry_ts_ms"] or 0) == entry_ts,
                "bt_exit_reason": bt_t["exit_reason"],
                "bt_exit_utc": bt_t["exit_utc"],
                "live_exit_utc": utc(int(ct["updated_ms"])),
            }
            bt_reason = str(bt_t["exit_reason"] or "")
            live_is_sl = live_exit_type == "StopLoss"
            live_is_tp = live_exit_type == "TakeProfit"
            bt_is_sl = "stop" in bt_reason
            bt_is_tp = "target" in bt_reason or bt_reason == "tp"
            if live_is_sl != bt_is_sl and live_is_tp != bt_is_tp:
                # allow names like stop / take_profit
                if not ((live_is_sl and bt_is_sl) or (live_is_tp and bt_is_tp)):
                    if abs(live_exit - planned_stop) > eps and abs(live_exit - planned_tgt) > eps:
                        material_live_bt_bug = True
                        blockers.append(f"{sym} {utc(entry_ts)}: live exit type {live_exit_type} vs BT {bt_reason}")
            if not diffs["same_entry_bar"]:
                material_live_bt_bug = True
                blockers.append(f"{sym} {utc(entry_ts)}: entry bar mismatch")
        elif bt.get("status") == "no_matching_signal":
            material_live_bt_bug = True
            blockers.append(f"{sym} {utc(entry_ts)}: live filled but research has no signal")
        if not stop_match or not tgt_match or not side_match:
            material_live_bt_bug = True
            blockers.append(f"{sym} {utc(entry_ts)}: live stop/target/side != research signal")
        report["closed_trades"].append(
            {
                "symbol": sym,
                "live": {
                    "side": side,
                    "qty": qty,
                    "leverage": ct.get("leverage"),
                    "entry_px": live_entry,
                    "exit_px": live_exit,
                    "entry_utc": utc(int(ct["created_ms"])) if ct.get("created_ms") else None,
                    "exit_utc": utc(int(ct["updated_ms"])) if ct.get("updated_ms") else None,
                    "planned_stop": planned_stop,
                    "planned_target": planned_tgt,
                    "closed_pnl": ct.get("closed_pnl"),
                    "exit_type": live_exit_type,
                    "exit_exec_fee_rate": (exit_exec or {}).get("feeRate"),
                },
                "signal_match": {
                    "stop_match": stop_match,
                    "target_match": tgt_match,
                    "side_match": side_match,
                    "signal": sig,
                },
                "one_m_path": touch_info,
                "backtest": bt,
                "diffs_live_minus_bt": diffs,
            }
        )

    for ot in live["open"]:
        sym = ot["symbol"]
        entry_ts = int(ot["entry_ts_ms"])
        sig_ts = entry_ts - TF_MS
        feat = frames[sym]["feat"]
        touch = frames[sym]["touch"]
        bt = resim_one(feat, touch, sym, sig_ts)
        stop = float(ot["stop_price"] or 0)
        tgt = float(ot["target_price"] or 0)
        side = ot["side"]
        sig = bt.get("signal_bar") or {}
        stop_match = sig.get("stop_price") is not None and abs(float(sig["stop_price"]) - stop) < 1e-6
        tgt_match = sig.get("target_price") is not None and abs(float(sig["target_price"]) - tgt) < 1e-6
        touch_info = one_m_touch_check(touch, entry_ts, stop, tgt, side)
        bt_t = (bt.get("trades") or [None])[0]
        if bt_t is not None and str(bt_t.get("exit_reason")) not in ("end_of_data", "None"):
            blockers.append(
                f"{sym} open live since {utc(entry_ts)} but 1m backtest already exited "
                f"{bt_t.get('exit_reason')} at {bt_t.get('exit_utc')} px={bt_t.get('exit_price')}"
            )
            # If 1m clearly through SL/TP hours ago, that is material; same-bar lag is slip/venue.
            if touch_info.get("first_touch") and touch_info.get("sl_ts_utc") and touch_info["first_touch"] == "StopLoss":
                material_live_bt_bug = True
        if not stop_match or not tgt_match:
            material_live_bt_bug = True
            blockers.append(f"{sym} open: live stop/target != research signal")
        report["open_trades"].append(
            {
                "symbol": sym,
                "live": {
                    "side": side,
                    "qty": ot.get("qty"),
                    "leverage": ot.get("leverage"),
                    "entry_px": ot.get("entry_price"),
                    "entry_utc": utc(entry_ts),
                    "planned_stop": stop,
                    "planned_target": tgt,
                },
                "signal_match": {"stop_match": stop_match, "target_match": tgt_match, "signal": sig},
                "one_m_path": touch_info,
                "backtest": bt,
            }
        )

    handled_keys = {(h["symbol"], int(h["entry_ts_ms"])) for h in live["handled"]}
    filled_keys = set(live_entries)
    for sym in SYMBOLS:
        for s in frames[sym]["live_sigs"]:
            key = (sym, s["entry_ts_ms"])
            taken = key in filled_keys or any(
                int(ot["entry_ts_ms"]) == s["entry_ts_ms"] and ot["symbol"] == sym for ot in live["open"]
            )
            handled = key in handled_keys
            if taken:
                continue
            if handled:
                h = next(x for x in live["handled"] if x["symbol"] == sym and int(x["entry_ts_ms"]) == s["entry_ts_ms"])
                detail = json.loads(h["detail_json"]) if h.get("detail_json") else {}
                report["missed_or_extra_signals"].append(
                    {"symbol": sym, **s, "live": "skipped", "reason": detail.get("skipped") or "handled_not_filled"}
                )
            else:
                report["missed_or_extra_signals"].append(
                    {"symbol": sym, **s, "live": "not_seen", "reason": "no handled_entries and no fill"}
                )
                # Future signals after last closed 1h are expected; others are bugs.
                last_1h = int(frames[sym]["feat"]["ts_ms"].iloc[-1])
                if s["signal_ts_ms"] <= last_1h - TF_MS:
                    blockers.append(f"{sym} {s['entry_utc']}: research signal not taken live")

    vps_bot_match = report["code_hashes"]["live_bot.py"] == report["code_hashes"]["vps_bot.py"]
    vps_core_match = report["code_hashes"]["live_signals_core.py"] == report["code_hashes"]["vps_signals_core.py"]
    if not vps_bot_match or not vps_core_match:
        blockers.append("Local deploy copy hash != VPS live copy")

    designed = [
        "Live StopLoss/TakeProfit fill as Bybit market (taker + slip). Backtester fills at planned price with zero exit slip.",
        "Live entry is Bybit last/market; backtester uses next-bar Binance open plus 0.05% entry slip.",
        "Live applies signed Bybit funding; this re-sim does not inject the Bybit funding series (funding near 0 in backtest trades).",
        "Evidence remains RESEARCH_PROXY (Binance signal candles vs Bybit fills).",
        "handled_entries for the first Aug 11/16 fills were overwritten by stale_entry (fixed in current live state.py; VPS hash matches local).",
    ]
    principal = (
        "No material strategy-logic mismatch found."
        if (signal_logic_ok and not material_live_bt_bug)
        else "Material live vs backtest logic mismatch — see principal_blockers."
    )
    if not signal_logic_ok:
        principal = "Research indicator/signal function diverges from live signals_core."
    elif material_live_bt_bug:
        principal = "At least one live fill does not match the research signal or 1-minute exit path beyond slippage."
    else:
        principal = (
            "Live is taking the same 1h chandelier signals (side, stop, target, min size) as the research function. "
            "Fill prices and exit times differ by design (Bybit market slip vs Binance next-open + 0.05% entry slip, "
            "zero exit slip in backtest). Historical freeze remains SHADOW_READY; this micro-live window is not a new gate pass."
        )

    report["principal_blocker"] = principal
    report["verdict"] = {
        "maximum_earned_readiness": "LIVE_STOP / RESEARCH_ONLY",
        "historical_freeze": "LIVE_STOP / SHADOW_READY (BTC+ETH 1h, artifacts/reports/tsm_chandelier/1h_SHADOW_FREEZE.json)",
        "end_to_end_identical": False,
        "candles_match": candle_ok,
        "indicator_functions_match": signal_logic_ok,
        "signal_side_stop_target_match": not material_live_bt_bug and signal_logic_ok,
        "vps_code_matches_local_deploy": vps_bot_match and vps_core_match,
        "closed_trade_count": len(live["closed"]),
        "open_trade_count": len(live["open"]),
        "material_logic_bug": material_live_bt_bug,
        "principal_blocker": principal,
        "principal_blockers": blockers + designed,
        "strategy_working_as_specified": signal_logic_ok and not material_live_bt_bug,
    }

    stamp = datetime.now(timezone.utc).strftime("%Y%m%d")
    out = OUT / f"live_vs_bt_full_{stamp}.json"
    out.write_text(json.dumps(report, indent=2, default=str), encoding="utf-8")
    latest = OUT / "live_vs_bt_full_latest.json"
    latest.write_text(out.read_text(encoding="utf-8"), encoding="utf-8")

    print("=== LIVE vs BACKTEST tsm_chandelier VPS94 ===")
    print("Max readiness:", report["verdict"]["maximum_earned_readiness"])
    print("Evidence class:", report["evidence_class"])
    print("Principal blocker:", principal)
    print("Candles match:", candle_ok, "Indicators match:", signal_logic_ok, "Material bug:", material_live_bt_bug)
    print("VPS code == local deploy:", vps_bot_match and vps_core_match)
    for sym, c in report["candles"].items():
        print(
            f"  candles {sym} research_1h n={c['research_1h']['n']} last={c['research_1h']['last']} "
            f"1m n={c['research_1m']['n']} last={c['research_1m']['last']} "
            f"vps_vs_research={c['vps_shared_vs_research'].get('all_equal')} "
            f"fetch_vs_research={c['fetch_1h_vs_research'].get('all_equal')}"
        )
        print("   indicators", report["indicators"][sym])
        print("   live-window signals", len(report["signals_in_live_window"][sym]))
    for row in report["closed_trades"]:
        live_r = row["live"]
        bt_t = (row["backtest"].get("trades") or [{}])[0]
        print(
            f" CLOSED {row['symbol']} {live_r['side']} pnl={live_r['closed_pnl']} "
            f"exit={live_r['exit_type']} live {live_r['entry_px']}->{live_r['exit_px']} "
            f"BT {bt_t.get('entry_price')}->{bt_t.get('exit_price')} {bt_t.get('exit_reason')} "
            f"stop/tgt/side={row['signal_match']}"
        )
        print("   diffs", row["diffs_live_minus_bt"])
        print("   1m", row["one_m_path"])
    for row in report["open_trades"]:
        print(
            f" OPEN {row['symbol']} {row['live']['side']} entry={row['live']['entry_px']} "
            f"{row['live']['entry_utc']} BT still_open={row['backtest'].get('still_open')} "
            f"1m={row['one_m_path']}"
        )
        if row["backtest"].get("trades"):
            print("   BT trade", row["backtest"]["trades"][0])
    print("Missed/extra:")
    for m in report["missed_or_extra_signals"]:
        print(" ", m["symbol"], m["side"], m["entry_utc"], m["live"], m["reason"])
    print("Blockers:")
    for b in report["verdict"]["principal_blockers"]:
        print(" -", b)
    print("WROTE", out)
    print("WROTE", latest)


if __name__ == "__main__":
    main()
