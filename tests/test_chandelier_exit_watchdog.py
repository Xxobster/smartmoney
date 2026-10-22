"""Live chandelier exit maintenance: missing stop, gap through the stop, max hold (no exchange calls)."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

SRC = Path(__file__).resolve().parents[1] / "deploy" / "tsm_chandelier" / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

import types  # noqa: E402

# The bot module imports the exchange SDK and the shared-candle reader; stub them (no network).
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
from chand.live.state import LiveState  # noqa: E402

H = 3_600_000
SOL = {"tick_size": 0.01, "qty_step": 0.1, "min_qty": 0.1, "min_notional": 5.0, "max_leverage": 50}


class FakeClient:
    def __init__(self, last: float, orders: list[dict], size: float = 0.2):
        self.last = last
        self.orders = orders
        self.size = size
        self.calls: list[tuple] = []

    def get_positions(self, symbol):
        return [{"size": str(self.size), "positionIdx": 2, "side": "Sell", "avgPrice": "107.56"}] if self.size else []

    def reduce_only_orders(self, symbol, idx):
        return list(self.orders)

    def get_ticker_last(self, symbol):
        return self.last

    def place_stop_limit(self, symbol, **kw):
        self.calls.append(("stop", kw))
        self.orders.append({"_kind": "stop", "triggerPrice": kw["stop_price"], "price": kw["limit_price"]})

    def place_maker_take_profit(self, symbol, **kw):
        self.calls.append(("tp", kw))

    def place_market_order(self, symbol, side, qty, position_idx, reduce_only=False, **kw):
        self.calls.append(("market", side, qty, reduce_only))
        self.size = 0

    def get_closed_pnl(self, *a, **k):
        return []

    def get_funding_settlements(self, *a, **k):
        return []

    def get_wallet_snapshot(self):
        return {}

    def get_server_time_ms(self):
        return 0


def make_bot(tmp_path, client):
    b = object.__new__(bot_mod.ChandLiveBot)
    b.symbol = "SOLUSDT"
    b.timeframe = "1h"
    b.instrument = SOL
    b.client = client
    b.state = LiveState(tmp_path / "s.sqlite")
    b.dry_run = False
    b.stop_limit_buffer = 0.003
    b.max_hold = 36
    b._last_snapshot_ms = None
    b.snapshot_interval_sec = 300
    b.state.set_open_trade(
        {
            "symbol": "SOLUSDT",
            "side": "short",
            "entry_ts_ms": 100 * H,
            "entry_price": 107.56,
            "stop_price": 110.28,
            "target_price": 99.77,
            "qty": 0.2,
            "leverage": 24,
            "position_idx": 2,
            "pattern": "chand_atr_band",
            "detail": {},
        }
    )
    return b


@pytest.fixture(autouse=True)
def _no_sleep(monkeypatch):
    monkeypatch.setattr(bot_mod.time, "sleep", lambda s: None)


def test_missing_stop_is_replaced_even_when_take_profit_rests(tmp_path):
    c = FakeClient(last=108.0, orders=[{"_kind": "limit", "price": "99.77"}])
    b = make_bot(tmp_path, c)
    b._ensure_maker_exits()
    kinds = [x[0] for x in c.calls]
    assert kinds == ["stop"]
    kw = c.calls[0][1]
    assert kw["stop_price"] == "110.28" and float(kw["limit_price"]) >= 110.28 * 1.003


def test_price_through_stop_without_stop_order_flattens(tmp_path):
    # 2026-09-20 case: SOL short, stop 110.28 gone, price ran to 117.97
    c = FakeClient(last=110.40, orders=[{"_kind": "limit", "price": "99.77"}])
    b = make_bot(tmp_path, c)
    b._ensure_maker_exits()
    assert ("market", "Buy", "0.2", True) in c.calls
    assert b.state.get_open_trade("SOLUSDT") is None


def test_gap_past_stop_limit_flattens_even_with_stop_resting(tmp_path):
    c = FakeClient(last=111.0, orders=[{"_kind": "stop", "triggerPrice": "110.28", "price": "110.62"}, {"_kind": "limit"}])
    b = make_bot(tmp_path, c)
    b._ensure_maker_exits()
    assert c.calls[0][0] == "market"


def test_stop_resting_and_price_inside_does_nothing(tmp_path):
    c = FakeClient(last=108.0, orders=[{"_kind": "stop", "triggerPrice": "110.28", "price": "110.62"}, {"_kind": "limit"}])
    b = make_bot(tmp_path, c)
    b._ensure_maker_exits()
    assert c.calls == []


def test_max_hold_flattens_at_entry_plus_36h_like_backtest(tmp_path):
    c = FakeClient(last=108.0, orders=[])
    b = make_bot(tmp_path, c)
    # last closed bar open = entry + 34h -> only 35 bars done: keep
    b._maybe_time_exit(100 * H + 34 * H)
    assert not any(x[0] == "market" for x in c.calls)
    # last closed bar open = entry + 35h -> its close is entry + 36h: flatten now
    b._maybe_time_exit(100 * H + 35 * H)
    assert ("market", "Buy", "0.2", True) in c.calls
