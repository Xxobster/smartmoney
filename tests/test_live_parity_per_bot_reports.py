"""Per-bot / per-account split of the combined live-parity JSON."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "research"))

from write_live_parity_per_bot_reports import ACCOUNT, _account_slice, _bot_slice, write_reports  # noqa: E402


def _mini_full() -> dict:
    return {
        "generated_utc": "2026-08-21T00:00:00+00:00",
        "evidence_class": "TEST",
        "principal_blocker": "designed slip",
        "candles": {
            "BTCUSDT": {"vps_shared_vs_research": {"all_equal": True}},
            "ETHUSDT": {"vps_shared_vs_research": {"all_equal": True}},
            "SOLUSDT": {"vps_shared_vs_research": {"all_equal": True}},
        },
        "indicators": {
            "BTCUSDT": {"research_vs_live_core_equal": True},
            "ETHUSDT": {"research_vs_live_core_equal": True},
            "SOLUSDT": {"research_vs_live_core_equal": True},
        },
        "signals_in_live_window": {"BTCUSDT": [], "ETHUSDT": [], "SOLUSDT": []},
        "closed_trades": [
            {
                "symbol": "BTCUSDT",
                "live": {"closed_pnl": 1.0, "side": "long"},
                "signal_match": {"side_match": True, "stop_match": True, "target_match": True},
            },
            {
                "symbol": "ETHUSDT",
                "live": {"closed_pnl": -0.2, "side": "short"},
                "signal_match": {"side_match": True, "stop_match": True, "target_match": True},
            },
        ],
        "open_trades": [{"symbol": "SOLUSDT", "live": {"side": "long"}}],
        "missed_or_extra_signals": [],
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
