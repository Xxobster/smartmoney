"""Stop-derived leverage with maintenance / mark buffers and safety haircut."""

from __future__ import annotations

import math
from dataclasses import dataclass

MAX_LEVERAGE = {
    "BTCUSDT": 125,
    "ETHUSDT": 100,
    "SOLUSDT": 50,
}

MM_BUFFER = 0.005
MARK_BUFFER = 0.002
MAINT_MARGIN_RATE = 0.004
# Extra safety haircut after floor(1/(sl+mm+mark)) — user-authorized live policy.
LEVERAGE_HAIRCUT = 0.80


@dataclass(frozen=True)
class MarginContract:
    mm_buffer: float = MM_BUFFER
    mark_buffer: float = MARK_BUFFER
    maint_margin_rate: float = MAINT_MARGIN_RATE
    max_margin_utilization: float = 0.60
    leverage_haircut: float = LEVERAGE_HAIRCUT


DEFAULT_CONTRACT = MarginContract()


def side_hint(entry: float, stop: float) -> str:
    return "long" if stop < entry else "short"


def liquidation_price(
    side: str,
    entry: float,
    leverage: int,
    *,
    contract: MarginContract = DEFAULT_CONTRACT,
) -> float:
    lev = max(1, int(leverage))
    mm = contract.maint_margin_rate
    if side == "long":
        return entry * (1.0 - (1.0 / lev) + mm)
    return entry * (1.0 + (1.0 / lev) - mm)


def stop_beyond_liquidation(
    side: str,
    entry: float,
    stop: float,
    leverage: int,
    *,
    contract: MarginContract = DEFAULT_CONTRACT,
) -> bool:
    liq = liquidation_price(side, entry, leverage, contract=contract)
    if side == "long":
        return stop > liq
    return stop < liq


def safe_leverage_vs_stop(
    side: str,
    entry: float,
    stop: float,
    leverage: int,
    *,
    contract: MarginContract = DEFAULT_CONTRACT,
) -> int:
    lev = max(1, int(leverage))
    while lev > 1 and not stop_beyond_liquidation(side, entry, stop, lev, contract=contract):
        lev -= 1
    return lev


def leverage_from_stop(
    entry: float,
    stop: float,
    *,
    symbol: str,
    contract: MarginContract = DEFAULT_CONTRACT,
    exchange_max: int | None = None,
) -> int:
    if entry <= 0 or not math.isfinite(entry) or not math.isfinite(stop):
        return 1
    sl_pct = abs(entry - stop) / entry
    denom = sl_pct + contract.mm_buffer + contract.mark_buffer
    if denom <= 0:
        return 1
    raw = int(math.floor(1.0 / denom))
    # Apply security haircut before exchange cap.
    raw = max(1, int(math.floor(raw * float(contract.leverage_haircut))))
    cap = int(MAX_LEVERAGE.get(symbol, 20))
    if exchange_max is not None:
        cap = min(cap, max(1, int(exchange_max)))
    lev = max(1, min(raw, cap))
    return safe_leverage_vs_stop(side_hint(entry, stop), entry, stop, lev, contract=contract)


def initial_margin(notional: float, leverage: int) -> float:
    return abs(notional) / max(1, int(leverage))
