"""Reduce-only maker take-profit / stop-limit payloads (no exchange Software Development Kit)."""

from __future__ import annotations

import math
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


def stop_limit_price(stop_price: float, *, is_long: bool, buffer: float, tick: float) -> float:
    """Limit price for the triggered stop: ``buffer`` past the trigger, on the tick grid.

    Long stop sells below the trigger, short stop buys above it, so the order is
    marketable when it triggers and fills up to ``buffer`` of slippage.
    """
    raw = stop_price * (1.0 - buffer) if is_long else stop_price * (1.0 + buffer)
    if tick <= 0:
        return raw
    steps = math.floor(raw / tick + 1e-9) if is_long else math.ceil(raw / tick - 1e-9)
    return steps * tick


def stop_limit_kwargs(
    symbol: str,
    *,
    exit_side: str,
    qty: str,
    stop_price: str,
    limit_price: str,
    position_idx: int,
    is_long: bool,
) -> dict[str, Any]:
    """Conditional reduce-only stop-limit, GTC (not Post-Only), limit ``buffer`` past the trigger.

    Post-Only was cancelled by Bybit when it triggered (it crossed the book), leaving the
    position without a stop (audit 2026-10-22). triggerDirection 2 = falling (long stop),
    1 = rising (short stop).
    """
    return {
        "category": "linear",
        "symbol": symbol,
        "side": exit_side,
        "orderType": "Limit",
        "qty": qty,
        "price": limit_price,
        "triggerPrice": stop_price,
        "triggerBy": "LastPrice",
        "triggerDirection": 2 if is_long else 1,
        "positionIdx": position_idx,
        "reduceOnly": True,
        "timeInForce": "GTC",
        "orderFilter": "StopOrder",
    }
