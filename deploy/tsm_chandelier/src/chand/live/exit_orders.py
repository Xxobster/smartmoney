"""Reduce-only maker take-profit / stop-limit payloads (no exchange Software Development Kit)."""

from __future__ import annotations

from typing import Any


def maker_take_profit_kwargs(
    symbol: str,
    *,
    exit_side: str,
    qty: str,
    price: str,
    position_idx: int,
) -> dict[str, Any]:
    """Resting reduce-only Post-Only limit at the take-profit price."""
    return {
        "category": "linear",
        "symbol": symbol,
        "side": exit_side,
        "orderType": "Limit",
        "qty": qty,
        "price": price,
        "positionIdx": position_idx,
        "reduceOnly": True,
        "timeInForce": "PostOnly",
    }


def maker_stop_limit_kwargs(
    symbol: str,
    *,
    exit_side: str,
    qty: str,
    stop_price: str,
    position_idx: int,
    is_long: bool,
) -> dict[str, Any]:
    """Conditional reduce-only stop-limit. Not a stop-market.

    triggerDirection 2 = falling (long stop), 1 = rising (short stop).
    """
    return {
        "category": "linear",
        "symbol": symbol,
        "side": exit_side,
        "orderType": "Limit",
        "qty": qty,
        "price": stop_price,
        "triggerPrice": stop_price,
        "triggerBy": "LastPrice",
        "triggerDirection": 2 if is_long else 1,
        "positionIdx": position_idx,
        "reduceOnly": True,
        "timeInForce": "PostOnly",
        "orderFilter": "StopOrder",
    }
