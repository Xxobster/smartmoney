"""Position size: 5% equity risk, round down, floor at exchange min."""

from __future__ import annotations

import sys
from pathlib import Path

SRC = Path(__file__).resolve().parents[1] / "deploy" / "tsm_chandelier" / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from chand.live.exit_orders import maker_stop_limit_kwargs, maker_take_profit_kwargs
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


def test_maker_sl_is_stop_limit_not_market():
    kw = maker_stop_limit_kwargs(
        "ETHUSDT",
        exit_side="Sell",
        qty="0.01",
        stop_price="3000",
        position_idx=1,
        is_long=True,
    )
    assert kw["orderType"] == "Limit"
    assert kw["orderFilter"] == "StopOrder"
    assert kw["triggerDirection"] == 2
    assert kw["timeInForce"] == "PostOnly"
    assert kw["reduceOnly"] is True
