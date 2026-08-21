#!/usr/bin/env python3
"""Compare VPS94 live tsm_chandelier trades vs local/VPS candle re-sim (same window)."""
from __future__ import annotations

import hashlib
import json
import sqlite3
import sys
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from engine.data_loader import load_ohlcv, research_db
from strategies.tsm_chandelier.signals import build_signal_frame, to_tradesim_signals

# deploy live core (should match research signals.py math)
sys.path.insert(0, str(ROOT / "deploy" / "tsm_chandelier" / "src"))
from chand.signals_core import build_signal_frame as live_build_signal_frame  # noqa: E402
from chand.live.signals import signals_from_frame  # noqa: E402

OUT = ROOT / "artifacts" / "reports" / "tsm_chandelier"
VPS_EXPORT = OUT / "vps94_parity_export"
LIVE_DB = OUT / "live_vps94_tsm_chandelier_live.sqlite"
# Live deploy started 2026-08-10 ~16:27 UTC; compare from 2026-08-10 00:00 UTC through now
SINCE_MS = int(datetime(2026, 8, 10, tzinfo=timezone.utc).timestamp() * 1000)
UNTIL_MS = int(datetime.now(timezone.utc).timestamp() * 1000)
SYMBOLS = ["BTCUSDT", "ETHUSDT", "SOLUSDT"]
TF_MS = 3_600_000


def utc(ms: int | None) -> str | None:
    if ms is None:
        return None
    return datetime.fromtimestamp(int(ms) / 1000, timezone.utc).isoformat()


def file_sha(path: Path) -> str:
    h = hashlib.sha256()
    h.update(path.read_bytes())
    return h.hexdigest()[:16]


def load_vps_csv(symbol: str) -> pd.DataFrame:
    full = VPS_EXPORT / f"{symbol}_1h_binance.csv"
    path = full if full.exists() else VPS_EXPORT / f"{symbol}_1h_binance_warmup400.csv"
    df = pd.read_csv(path)
    df["ts_ms"] = df["ts_ms"].astype("int64")
    return df.sort_values("ts_ms").reset_index(drop=True)


def compare_ohlcv(a: pd.DataFrame, b: pd.DataFrame, label_a: str, label_b: str) -> dict:
    """Align on ts_ms and compare OHLC."""
    m = a.merge(b, on="ts_ms", suffixes=("_a", "_b"), how="outer", indicator=True)
    both = m[m["_merge"] == "both"].copy()
    only_a = int((m["_merge"] == "left_only").sum())
    only_b = int((m["_merge"] == "right_only").sum())
    diffs = {}
    n_mismatch = 0
    for col in ["open", "high", "low", "close", "volume"]:
        if both.empty:
            diffs[col] = {"max_abs": None, "n_ne": None}
            continue
        da = both[f"{col}_a"].to_numpy(float)
        db = both[f"{col}_b"].to_numpy(float)
        ne = ~np.isclose(da, db, rtol=0, atol=1e-8, equal_nan=True)
        n_ne = int(ne.sum())
        n_mismatch += n_ne
        diffs[col] = {
            "max_abs": float(np.nanmax(np.abs(da - db))) if len(da) else None,
            "n_ne": n_ne,
        }
    # window filter for report
    win = both[(both["ts_ms"] >= SINCE_MS) & (both["ts_ms"] < UNTIL_MS)]
    return {
        "label_a": label_a,
        "label_b": label_b,
        "n_a": int(len(a)),
        "n_b": int(len(b)),
        "n_both": int(len(both)),
        "only_a": only_a,
        "only_b": only_b,
        "n_mismatch_cells": n_mismatch,
        "ohlc_exact_match": n_mismatch == 0 and only_a == 0 and only_b == 0,
        "window_both": int(len(win)),
        "window_first": utc(int(win["ts_ms"].iloc[0])) if len(win) else None,
        "window_last": utc(int(win["ts_ms"].iloc[-1])) if len(win) else None,
        "diffs": diffs,
    }


def signal_rows(feat: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for i in range(len(feat)):
        long_i = bool(feat["long_signal"].iloc[i])
        short_i = bool(feat["short_signal"].iloc[i])
        if long_i == short_i:
            continue
        ts = int(feat["ts_ms"].iloc[i])
        if ts < SINCE_MS or ts >= UNTIL_MS:
            continue
        side = "long" if long_i else "short"
        rows.append(
            {
                "signal_ts_ms": ts,
                "signal_utc": utc(ts),
                "entry_ts_ms": ts + TF_MS,
                "entry_utc": utc(ts + TF_MS),
                "side": side,
                "close": float(feat["close"].iloc[i]),
                "stop": float(feat["stop_price"].iloc[i]),
                "target": float(feat["target_price"].iloc[i]),
                "atr": float(feat["atr"].iloc[i]),
            }
        )
    return pd.DataFrame(rows)


def load_live_state() -> dict:
    con = sqlite3.connect(LIVE_DB)
    con.row_factory = sqlite3.Row
    out = {
        "open_trades": [dict(r) for r in con.execute("select * from open_trades")],
        "handled": [dict(r) for r in con.execute("select * from handled_entries order by entry_ts_ms")],
        "closed": [dict(r) for r in con.execute("select * from closed_trades")],
        "entry_filled_events": [
            dict(r)
            for r in con.execute(
                "select id, ts_utc, symbol, kind, detail_json from events where kind='entry_filled' order by id"
            )
        ],
        "stale_skips": [
            dict(r)
            for r in con.execute(
                "select id, ts_utc, symbol, kind, detail_json from events "
                "where kind='entry_timing' and detail_json like '%stale_entry%' order by id"
            )
        ],
    }
    con.close()
    return out


def main() -> None:
    report: dict = {
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "period": {"since_ms": SINCE_MS, "until_ms": UNTIL_MS, "since_utc": utc(SINCE_MS), "until_utc": utc(UNTIL_MS)},
        "readiness_max": "LIVE_STOP / RESEARCH_ONLY",
        "evidence_class": "FORWARD_MICRO_LIVE_RECONCILE (RESEARCH_PROXY candles)",
        "code_hashes": {
            "research_signals.py": file_sha(ROOT / "strategies" / "tsm_chandelier" / "signals.py"),
            "live_signals_core.py": file_sha(ROOT / "deploy" / "tsm_chandelier" / "src" / "chand" / "signals_core.py"),
        },
        "symbols": {},
        "live": {},
        "verdict": {},
    }

    # code identity: research vs live core function text via outputs
    live = load_live_state()
    report["live"] = {
        "open_trades": [
            {
                "symbol": t["symbol"],
                "side": t["side"],
                "entry_ts_ms": t["entry_ts_ms"],
                "entry_utc": utc(t["entry_ts_ms"]),
                "entry_price": t["entry_price"],
                "stop_price": t["stop_price"],
                "target_price": t["target_price"],
                "qty": t["qty"],
                "leverage": t["leverage"],
                "created_utc": t.get("created_utc"),
            }
            for t in live["open_trades"]
        ],
        "handled": live["handled"],
        "closed_n": len(live["closed"]),
        "entry_filled_events": live["entry_filled_events"],
    }

    try:
        local_db = research_db()
    except Exception:
        local_db = None
    all_signal_match = True
    all_data_match = True
    all_logic_match = True

    for sym in SYMBOLS:
        if local_db is not None:
            try:
                local = load_ohlcv(local_db, sym, "1h", source="binance")
                local = local[local["ts_ms"] < UNTIL_MS].copy()
            except Exception:
                local = pd.DataFrame()
        else:
            local = pd.DataFrame()
        vps = load_vps_csv(sym)
        vps = vps[vps["ts_ms"] < UNTIL_MS].copy()

        # compare overlapping window from max(local.min, vps.min) but focus since deploy
        # Restrict local to same ts set as vps warmup for fair OHLC compare on recent bars
        overlap_start = max(int(vps["ts_ms"].min()), int(local["ts_ms"].min())) if len(local) and len(vps) else None
        if overlap_start is None:
            report["symbols"][sym] = {"status": "missing_data"}
            all_data_match = False
            continue
        local_w = local[local["ts_ms"] >= overlap_start][
            ["ts_ms", "open", "high", "low", "close", "volume"]
        ].reset_index(drop=True)
        vps_w = vps[vps["ts_ms"] >= overlap_start][
            ["ts_ms", "open", "high", "low", "close", "volume"]
        ].reset_index(drop=True)
        data_cmp = compare_ohlcv(local_w, vps_w, "local_research_db", "vps_shared_candles")
        if not data_cmp["ohlc_exact_match"]:
            # allow local to have fewer recent bars (not updated) — check VPS-only on recent window
            win_vps = vps_w[(vps_w["ts_ms"] >= SINCE_MS) & (vps_w["ts_ms"] < UNTIL_MS)]
            win_local = local_w[(local_w["ts_ms"] >= SINCE_MS) & (local_w["ts_ms"] < UNTIL_MS)]
            data_cmp_win = compare_ohlcv(win_local, win_vps, "local_window", "vps_window")
            data_cmp["window_compare"] = data_cmp_win
            if not data_cmp_win.get("ohlc_exact_match"):
                all_data_match = False
        else:
            data_cmp["window_compare"] = None

        # indicator/logic: research builder vs live builder on VPS candles (authoritative live feed)
        feat_research = build_signal_frame(vps)
        feat_live = live_build_signal_frame(vps)
        logic_cols = ["atr", "long_signal", "short_signal", "stop_price", "target_price"]
        logic_equal = True
        logic_detail = {}
        for c in logic_cols:
            a = feat_research[c].to_numpy()
            b = feat_live[c].to_numpy()
            if a.dtype == bool or b.dtype == bool or c in ("long_signal", "short_signal"):
                eq = bool(np.array_equal(a.astype(bool), b.astype(bool)))
            else:
                eq = bool(np.allclose(a.astype(float), b.astype(float), equal_nan=True))
            logic_detail[c] = eq
            logic_equal = logic_equal and eq
        if not logic_equal:
            all_logic_match = False

        sig_vps = signal_rows(feat_research)
        # also signals from local research DB candles (may lag)
        feat_local = build_signal_frame(local) if len(local) else pd.DataFrame()
        sig_local = signal_rows(feat_local) if len(feat_local) else pd.DataFrame()

        live_sigs = signals_from_frame(feat_live, timeframe="1h")
        live_sigs_win = [
            asdict(s)
            for s in live_sigs
            if SINCE_MS <= int(s.signal_ts_ms) < UNTIL_MS
        ]

        # match live open/filled/closed vs expected
        expected = sig_vps.to_dict(orient="records") if len(sig_vps) else []
        filled = []
        for ev in live["entry_filled_events"]:
            if ev["symbol"] != sym:
                continue
            detail = json.loads(ev["detail_json"] or "{}")
            nested = detail.get("detail") or {}
            sigd = detail.get("signal") or nested.get("signal") or {}
            filld = detail.get("fill") or nested.get("fill") or {}
            filled.append(
                {
                    "event_ts_utc": ev["ts_utc"],
                    "side": detail.get("side") or sigd.get("side"),
                    "entry_ts_ms": detail.get("entry_ts_ms") or sigd.get("entry_ts_ms"),
                    "signal_ts_ms": detail.get("signal_ts_ms") or sigd.get("signal_ts_ms"),
                    "entry_price": (
                        detail.get("entry_price")
                        or filld.get("avgPrice")
                        or nested.get("entry_est")
                        or detail.get("entry_est")
                    ),
                    "stop": (
                        detail.get("stop_price")
                        or detail.get("stop")
                        or sigd.get("stop_price")
                        or nested.get("stop")
                    ),
                    "target": (
                        detail.get("target_price")
                        or detail.get("target")
                        or sigd.get("target_price")
                        or nested.get("target")
                    ),
                    "qty": detail.get("qty"),
                    "leverage": detail.get("leverage"),
                    "source": "entry_filled",
                }
            )
        for t in live["closed"]:
            if t.get("symbol") != sym:
                continue
            filled.append(
                {
                    "event_ts_utc": t.get("recorded_utc"),
                    "side": "long" if str(t.get("side")) == "Buy" else "short",
                    "entry_ts_ms": t.get("planned_entry_ts_ms"),
                    "signal_ts_ms": None,
                    "entry_price": t.get("avg_entry_price"),
                    "stop": t.get("planned_stop"),
                    "target": t.get("planned_target"),
                    "exit_price": t.get("avg_exit_price"),
                    "closed_pnl": t.get("closed_pnl"),
                    "qty": t.get("qty"),
                    "source": "closed_trade",
                }
            )
        open_t = [t for t in live["open_trades"] if t["symbol"] == sym]

        matches = []
        for exp in expected:
            hit = None
            for f in filled + [
                {
                    "side": t["side"],
                    "entry_ts_ms": t["entry_ts_ms"],
                    "signal_ts_ms": json.loads(t.get("detail_json") or "{}").get("signal_ts_ms"),
                    "entry_price": t["entry_price"],
                    "stop": t["stop_price"],
                    "target": t["target_price"],
                    "from_open": True,
                }
                for t in open_t
            ]:
                if int(f.get("entry_ts_ms") or -1) == int(exp["entry_ts_ms"]) and f.get("side") == exp["side"]:
                    hit = f
                    break
            stop_match = None
            tgt_match = None
            if hit is not None:
                try:
                    stop_match = abs(float(hit["stop"]) - float(exp["stop"])) < 1e-4
                    tgt_match = abs(float(hit["target"]) - float(exp["target"])) < 1e-4
                except Exception:
                    stop_match = tgt_match = False
            slip_bps = None
            if hit is not None and hit.get("entry_price") is not None and exp.get("close"):
                fill_px = float(hit["entry_price"])
                ref = float(exp["close"])
                raw = (fill_px - ref) / ref * 10_000.0
                # adverse: short wants fill below close; long wants fill above
                slip_bps = -raw if exp["side"] == "short" else raw
            matches.append(
                {
                    "expected": exp,
                    "live_hit": hit is not None,
                    "live": hit,
                    "stop_match": stop_match,
                    "target_match": tgt_match,
                    "fill_vs_signal_close_slip_bps": slip_bps,
                }
            )
            if hit is None or not stop_match or not tgt_match:
                all_signal_match = False

        # if expected empty but live filled — mismatch
        if not expected and (filled or open_t):
            all_signal_match = False

        report["symbols"][sym] = {
            "data_compare": data_cmp,
            "logic_research_vs_live_core_equal": logic_equal,
            "logic_detail": logic_detail,
            "expected_signals_on_vps_candles": expected,
            "expected_signals_on_local_db": sig_local.to_dict(orient="records") if len(sig_local) else [],
            "live_signals_helper_count": len(live_sigs_win),
            "live_filled": filled,
            "live_open": [
                {
                    "side": t["side"],
                    "entry_ts_ms": t["entry_ts_ms"],
                    "entry_utc": utc(t["entry_ts_ms"]),
                    "entry_price": t["entry_price"],
                    "stop_price": t["stop_price"],
                    "target_price": t["target_price"],
                }
                for t in open_t
            ],
            "matches": matches,
        }

    report["verdict"] = {
        "data_similar_exact_on_overlap_window": all_data_match,
        "indicator_strategy_logic_identical_research_vs_live_core": all_logic_match,
        "live_entries_match_resim_signals_stops_targets": all_signal_match,
        "principal_blockers": [],
        "maximum_earned_readiness": "LIVE_STOP / RESEARCH_ONLY",
        "note": (
            "Historical SHADOW_READY unchanged; this is forward micro-live reconciliation only. "
            "Exact live/backtest identity also requires same fill model (Bybit taker vs sim), "
            "margin mode, and protective-order success."
        ),
    }
    blockers = report["verdict"]["principal_blockers"]
    if not all_data_match:
        blockers.append("Local research OHLCV does not exactly match VPS shared Binance 1h on the live window (local may be stale or diverge).")
    if not all_logic_match:
        blockers.append("Research signals.py vs deploy signals_core.py produce different indicator/signal outputs.")
    if not all_signal_match:
        blockers.append("Live fills/open trades do not match re-sim signals/stops/targets on VPS candles.")
    # always note known operational issues from prior inspection
    blockers.append(
        "botsgeneral freshness: at each hour open, last complete 1h bar often lags ~2h briefly (collector delay) → bot waits / can skip entries."
    )
    blockers.append(
        "Protective stop set_trading_stop returned ErrCode 34040 (not modified) after BTC/ETH fills — verify exchange SL/TP actually present."
    )
    blockers.append(
        "Evidence class remains RESEARCH_PROXY (Binance Last candles vs Bybit execution)."
    )

    out_path = OUT / "live_vs_backtest_parity_vps94.json"
    out_path.write_text(json.dumps(report, indent=2, default=str), encoding="utf-8")

    # human summary
    print("=== LIVE vs BACKTEST PARITY (VPS 94) ===")
    print("Period:", report["period"]["since_utc"], "->", report["period"]["until_utc"])
    print("Max readiness:", report["verdict"]["maximum_earned_readiness"])
    print("Evidence class:", report["evidence_class"])
    print("Code hashes:", report["code_hashes"])
    print("Logic research==live core:", all_logic_match)
    print("Data window exact:", all_data_match)
    print("Live entries match resim:", all_signal_match)
    for sym, block in report["symbols"].items():
        print(f"\n--- {sym} ---")
        dc = block.get("data_compare", {})
        wc = dc.get("window_compare") or dc
        print("  data window exact:", wc.get("ohlc_exact_match"), "both=", wc.get("n_both"), "only_local=", wc.get("only_a"), "only_vps=", wc.get("only_b"))
        print("  logic equal:", block.get("logic_research_vs_live_core_equal"))
        print("  expected signals:", block.get("expected_signals_on_vps_candles"))
        print("  live open:", block.get("live_open"))
        print("  matches:", json.dumps(block.get("matches"), default=str)[:800])
    print("\nBlockers:")
    for b in blockers:
        print(" -", b.encode("ascii", "replace").decode("ascii") if isinstance(b, str) else b)
    print("Wrote", out_path)


if __name__ == "__main__":
    main()
