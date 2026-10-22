"""Position size: 5% equity risk, round down, floor at exchange min."""

from __future__ import annotations

import sys
from pathlib import Path

SRC = Path(__file__).resolve().parents[1] / "deploy" / "tsm_chandelier" / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from chand.live.exit_orders import maker_take_profit_kwargs, stop_limit_kwargs, stop_limit_price
from chand.live.sizing import size_qty_risk_with_min_floor


BTC = {
    "min_qty": 0.001,
    "qty_step": 0.001,
    "min_notional": 100.0,
    "tick_size": 0.1,
}


def test_tiny_wallet_5pct_floors_to_btc_min():
    # 5% of 18.97 USDT = 0.9485 cash risk. 2% stop on 110_000 → raw qty << 0.001.
    qty = size_qty_risk_with_min_floor(
        equity=18.97,
        risk_frac=0.05,
        entry=110_000.0,
        stop=107_800.0,
        instrument=BTC,
    )
    assert qty == 0.001


def test_large_wallet_rounds_down_to_step():
    # 5% of 10_000 = 500 cash risk / 2200 per BTC = 0.2272 → floor 0.227
    qty = size_qty_risk_with_min_floor(
        equity=10_000.0,
        risk_frac=0.05,
        entry=110_000.0,
        stop=107_800.0,
        instrument=BTC,
        notional_buffer=0.0,
    )
    assert qty == 0.227


def test_maker_tp_is_post_only_reduce_only():
    kw = maker_take_profit_kwargs(
        "ETHUSDT", exit_side="Sell", qty="0.01", price="4000", position_idx=1
    )
    assert kw["orderType"] == "Limit"
    assert kw["timeInForce"] == "PostOnly"
    assert kw["reduceOnly"] is True
    assert "triggerPrice" not in kw


def test_sl_is_gtc_stop_limit_past_trigger():
    kw = stop_limit_kwargs(
        "ETHUSDT",
        exit_side="Sell",
        qty="0.01",
        stop_price="3000",
        limit_price="2991",
        position_idx=1,
        is_long=True,
    )
    assert kw["orderType"] == "Limit"
    assert kw["orderFilter"] == "StopOrder"
    assert kw["triggerDirection"] == 2
    # Post-Only was cancelled by Bybit on trigger (audit 2026-10-22)
    assert kw["timeInForce"] == "GTC"
    assert kw["reduceOnly"] is True
    assert kw["price"] == "2991" and kw["triggerPrice"] == "3000"


def test_stop_limit_price_buffer_rounds_away_from_market():
    assert abs(stop_limit_price(100.0, is_long=True, buffer=0.003, tick=0.01) - 99.70) < 1e-9
    assert abs(stop_limit_price(100.0, is_long=False, buffer=0.003, tick=0.01) - 100.30) < 1e-9
    assert stop_limit_price(105.44, is_long=True, buffer=0.003, tick=0.01) <= 105.44 * 0.997
    assert stop_limit_price(110.28, is_long=False, buffer=0.003, tick=0.01) >= 110.28 * 1.003
