"""Closeness percent scoring for live vs backtest."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "research"))

from live_parity_closeness import (  # noqa: E402
    candles_pct,
    fmt_pct,
    score_account,
    signals_pct,
)
from write_live_parity_per_bot_reports import ACCOUNT, _account_slice, _bot_slice, write_reports  # noqa: E402


def _mini_full() -> dict:
    return {
        "generated_utc": "2026-08-21T00:00:00+00:00",
        "evidence_class": "TEST",
        "principal_blocker": "designed slip",
        "candles": {
            "BTCUSDT": {
                "vps_shared_vs_research": {
                    "n_overlap": 800,
                    "all_equal": True,
                    "n_diff": {"open": 0, "high": 0, "low": 0, "close": 0},
                }
            },
            "ETHUSDT": {
                "vps_shared_vs_research": {
                    "n_overlap": 800,
                    "all_equal": False,
                    "n_diff": {"open": 8, "high": 0, "low": 0, "close": 0},
                }
            },
            "SOLUSDT": {"vps_shared_vs_research": {"all_equal": True}},
        },
        "indicators": {
            "BTCUSDT": {
                "research_vs_live_core_equal": True,
                "detail": {
                    "atr": True,
                    "long_signal": True,
                    "short_signal": True,
                    "stop_price": True,
                    "target_price": True,
                },
            },
            "ETHUSDT": {"research_vs_live_core_equal": True, "detail": {"atr": True, "long_signal": False}},
            "SOLUSDT": {"research_vs_live_core_equal": True},
        },
        "signals_in_live_window": {
            "BTCUSDT": [
                {"entry_utc": "2026-08-11T15:00:00+00:00", "side": "short"},
                {"entry_utc": "2026-08-19T15:00:00+00:00", "side": "long"},
            ],
            "ETHUSDT": [{"entry_utc": "2026-08-10T10:00:00+00:00", "side": "long"}],
            "SOLUSDT": [],
        },
        "closed_trades": [
            {
                "symbol": "BTCUSDT",
                "live": {
                    "closed_pnl": 1.0,
                    "side": "short",
                    "entry_utc": "2026-08-11T15:00:25+00:00",
                    "entry_px": 100.1,
                    "exit_px": 99.0,
                    "exit_type": "StopLoss",
                },
                "signal_match": {"side_match": True, "stop_match": True, "target_match": True},
                "diffs_live_minus_bt": {"same_entry_bar": True, "bt_exit_reason": "stop"},
                "one_m_path": {"first_touch": "StopLoss"},
                "backtest": {
                    "trades": [
                        {"entry_price": 100.0, "exit_price": 99.0, "exit_reason": "stop"}
                    ]
                },
            },
            {
                "symbol": "ETHUSDT",
                "live": {"closed_pnl": -0.2, "side": "short", "entry_utc": "2026-08-09T01:00:00+00:00"},
                "signal_match": {"side_match": True, "stop_match": True, "target_match": True},
            },
        ],
        "open_trades": [{"symbol": "SOLUSDT", "live": {"side": "long"}}],
        "missed_or_extra_signals": [
            {
                "symbol": "BTCUSDT",
                "entry_utc": "2026-08-19T15:00:00+00:00",
                "side": "long",
                "reason": "in_position",
            },
            {
                "symbol": "ETHUSDT",
                "entry_utc": "2026-08-10T10:00:00+00:00",
                "side": "long",
                "reason": "not_seen",
            },
        ],
        "verdict": {"strategy_working_as_specified": True, "material_logic_bug": False},
    }


def test_bot_slice_keeps_only_that_symbol() -> None:
    btc = _bot_slice(_mini_full(), "BTCUSDT")
    assert btc["account"] == ACCOUNT
    assert btc["bot_unit"] == "tsm-chandelier@BTCUSDT"
    assert len(btc["closed_trades"]) == 1
    assert btc["closed_trades"][0]["symbol"] == "BTCUSDT"
    assert btc["open_trades"] == []
    assert abs(btc["closed_net_pnl_usdt"] - 1.0) < 1e-12


def test_account_rollup_sums_closed_pnl(tmp_path: Path) -> None:
    full = _mini_full()
    bots = {s: _bot_slice(full, s) for s in ("BTCUSDT", "ETHUSDT", "SOLUSDT")}
    acc = _account_slice(full, bots)
    assert acc["account"] == ACCOUNT
    assert acc["closed_trade_count"] == 2
    assert acc["open_trade_count"] == 1
    assert abs(acc["closed_net_pnl_usdt"] - 0.8) < 1e-12
    written = write_reports(full, out_dir=tmp_path)
    assert (tmp_path / "by_account" / f"{ACCOUNT}.md").exists()
    assert (tmp_path / "by_bot" / f"{ACCOUNT}_SOLUSDT.json").exists()
    sol = json.loads(written["bot_SOLUSDT_json"].read_text(encoding="utf-8"))
    assert sol["exploratory"] is True
    assert sol["verdict"]["closed_trade_count"] == 0
    assert sol["verdict"]["open_trade_count"] == 1
    md = (tmp_path / "by_account" / f"{ACCOUNT}.md").read_text(encoding="utf-8")
    assert "Closeness" in md
    assert "candles" in md.lower() or "Candles" in md


def test_closeness_perfect_logic_and_valid_skip() -> None:
    btc = _bot_slice(_mini_full(), "BTCUSDT")
    c = btc["closeness"]
    assert c["candles_pct"] == 100.0
    assert c["calculations_pct"] == 100.0
    assert c["signals_pct"] == 100.0
    assert c["entries_exits_pct"] == 100.0
    assert c["fill_price_pct"] is not None
    assert c["fill_price_pct"] > 99.0


def test_closeness_penalizes_candle_and_missed_signal() -> None:
    eth = _bot_slice(_mini_full(), "ETHUSDT")
    c = eth["closeness"]
    assert abs(c["candles_pct"] - 100.0 * (1.0 - 8 / 800)) < 1e-9
    assert c["calculations_pct"] == 50.0
    assert c["signals_pct"] == 0.0


def test_fmt_pct_and_account_mean() -> None:
    assert fmt_pct(100.0) == "100%"
    assert fmt_pct(None) == "n/a"
    scores = [
        {"candles_pct": 100.0, "calculations_pct": 100.0, "signals_pct": 100.0, "entries_exits_pct": 100.0, "fill_price_pct": 99.9, "overall_pct": 100.0},
        {"candles_pct": 90.0, "calculations_pct": 50.0, "signals_pct": 0.0, "entries_exits_pct": 100.0, "fill_price_pct": 99.0, "overall_pct": 60.0},
    ]
    acc = score_account(scores)
    assert acc["candles_pct"] == 95.0
    assert acc["signals_pct"] == 50.0


def test_candles_pct_no_overlap_uses_flag() -> None:
    assert candles_pct({"vps_shared_vs_research": {"n_overlap": 0, "all_equal": True}}) == 100.0
    assert signals_pct({"signals_in_live_window": []}) is None
