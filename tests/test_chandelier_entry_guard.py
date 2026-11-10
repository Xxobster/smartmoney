"""Entry guard (2026-11-10): no market entry when the price already ran into the planned stop, or the price cannot be read."""

from __future__ import annotations

import sys
import types
from pathlib import Path

import pytest

SRC = Path(__file__).resolve().parents[1] / "deploy" / "tsm_chandelier" / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

for name, attrs in {
    "pybit": {},
    "pybit.unified_trading": {"HTTP": object},
    "live_candles": {},
    "live_candles.reader": {"load_ohlcv": None, "shared_db_path": None},
    "live_candles.shared": {"candles_fresh": None, "interval_ms": None, "latest_ts_ms": None},
}.items():
    if name not in sys.modules:
        try:
            __import__(name)
        except ImportError:
            mod = types.ModuleType(name)
            mod.__dict__.update(attrs)
            sys.modules[name] = mod

from chand.live import bot as bot_mod  # noqa: E402
from chand.live.entry_guard import (  # noqa: E402
    REASON_CROSSED, REASON_OK, REASON_PRICE_FAIL, REASON_TOO_CLOSE, evaluate_entry_guard)
from chand.live.signals import LiveSignal  # noqa: E402
from chand.live.state import LiveState  # noqa: E402

H = 3_600_000
BTC = {"tick_size": 0.1, "qty_step": 0.001, "min_qty": 0.001, "min_notional": 5.0, "max_leverage": 100}


# ---- pure function -----------------------------------------------------------------------------------------------
def test_2026_11_08_btc_short_replay_is_skipped():
    """Planned stop 74 332.4, market price 74 345.3 (13 points above the stop), entry reference at the hourly open."""
    v = evaluate_entry_guard(side="short", price=74_345.3, stop=74_332.4, entry_ref=74_097.4)
    assert not v.ok and v.reason == REASON_CROSSED and v.remaining_distance < 0


def test_normal_short_and_long_enter():
    assert evaluate_entry_guard(side="short", price=74_100.0, stop=74_332.4, entry_ref=74_097.4).ok
    v = evaluate_entry_guard(side="long", price=100.1, stop=98.0, entry_ref=100.0)
    assert v.ok and v.reason == REASON_OK and v.remaining_frac > 0.9


def test_distance_below_25_percent_is_skipped_and_boundary():
    planned = 100.0
    # long: entry_ref 1000, stop 900. price 924 -> remaining 24 (24 % of 100) -> skip ; 926 -> 26 % -> enter
    assert evaluate_entry_guard(side="long", price=924.0, stop=900.0, entry_ref=1000.0).reason == REASON_TOO_CLOSE
    assert evaluate_entry_guard(side="long", price=926.0, stop=900.0, entry_ref=1000.0).ok
    assert evaluate_entry_guard(side="short", price=1076.0, stop=1100.0, entry_ref=1000.0).reason == REASON_TOO_CLOSE
    assert evaluate_entry_guard(side="short", price=1074.0, stop=1100.0, entry_ref=1000.0).ok
    assert planned == 100.0


def test_crossed_stop_long_and_exactly_on_the_stop():
    assert evaluate_entry_guard(side="long", price=97.0, stop=98.0, entry_ref=100.0).reason == REASON_CROSSED
    assert evaluate_entry_guard(side="long", price=98.0, stop=98.0, entry_ref=100.0).reason == REASON_CROSSED
    assert evaluate_entry_guard(side="short", price=102.0, stop=102.0, entry_ref=100.0).reason == REASON_CROSSED


@pytest.mark.parametrize("bad", [None, float("nan"), 0.0, -1.0, "abc"])
def test_unreadable_price_fails_closed(bad):
    v = evaluate_entry_guard(side="short", price=bad, stop=74_332.4, entry_ref=74_097.4)
    assert not v.ok and v.reason == REASON_PRICE_FAIL


# ---- bot level: _enter ---------------------------------------------------------------------------------------------
class Client:
    def __init__(self, last):
        self.last = last
        self.calls = []

    def get_ticker_last(self, symbol):
        if isinstance(self.last, Exception):
            raise self.last
        return self.last

    def set_leverage(self, *a):
        self.calls.append(("leverage", a))

    def place_market_order(self, symbol, side, qty, position_idx, reduce_only=False, **kw):
        self.calls.append(("market", side, qty, reduce_only))

    def wait_for_position_fill(self, symbol, idx):
        return {"avgPrice": "74097.4", "size": "0.017"}


def make_bot(tmp_path, client):
    b = object.__new__(bot_mod.ChandLiveBot)
    b.symbol = "BTCUSDT"
    b.timeframe = "1h"
    b.instrument = BTC
    b.client = client
    b.state = LiveState(tmp_path / "s.sqlite")
    b.dry_run = False
    b.use_min_size = False
    b.account_margin_mode = "isolated"
    b._open_exchange_position = lambda: None
    b._size_order = lambda sig, entry: (0.017, 50, 17.7)
    b._place_maker_exits = lambda **k: None
    b._snapshot = lambda *a, **k: None
    b._now_ms = lambda: 400 * H + 33_000
    return b


def sig(side="short", stop=74_332.4, ref=74_097.4):
    return LiveSignal(side=side, signal_ts_ms=399 * H, entry_ts_ms=400 * H, entry_ref_price=ref, stop_price=stop,
                      target_price=73_392.5, pattern="chand_atr_band", stack_score=1.0)


def test_enter_skips_the_replayed_btc_case_and_logs(tmp_path, caplog):
    c = Client(74_345.3)
    b = make_bot(tmp_path, c)
    with caplog.at_level("WARNING"):
        b._enter(sig(), now_ms=400 * H + 33_000, last_closed_ts_ms=399 * H)
    assert not [x for x in c.calls if x[0] == "market"], "no market order may be sent"
    assert "ENTRY_SKIP_STOP_PROXIMITY" in caplog.text and REASON_CROSSED in caplog.text
    assert b.state.entry_handled("BTCUSDT", 400 * H), "a proximity skip is final for this bar"
    assert b.state.get_open_trade("BTCUSDT") is None


def test_enter_normal_case_sends_the_market_order(tmp_path):
    c = Client(74_100.0)
    b = make_bot(tmp_path, c)
    b._enter(sig(), now_ms=400 * H + 33_000, last_closed_ts_ms=399 * H)
    assert [x for x in c.calls if x[0] == "market" and not x[3]], "market entry expected"
    assert b.state.get_open_trade("BTCUSDT") is not None


def test_enter_price_read_failure_skips_and_may_retry(tmp_path, caplog):
    c = Client(RuntimeError("ticker down"))
    b = make_bot(tmp_path, c)
    with caplog.at_level("WARNING"):
        b._enter(sig(), now_ms=400 * H + 33_000, last_closed_ts_ms=399 * H)
    assert not [x for x in c.calls if x[0] == "market"]
    assert "ENTRY_SKIP_STOP_PROXIMITY" in caplog.text and REASON_PRICE_FAIL in caplog.text
    assert not b.state.entry_handled("BTCUSDT", 400 * H), "fail closed, but the next poll may retry within max_entry_delay_sec"
    c.last = 74_100.0
    b._enter(sig(), now_ms=400 * H + 40_000, last_closed_ts_ms=399 * H)
    assert [x for x in c.calls if x[0] == "market"]
