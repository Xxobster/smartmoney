"""Pure position-sizing helpers (no exchange Software Development Kit imports)."""

from __future__ import annotations

import math


def round_qty(qty: float, step: float, min_qty: float) -> float:
    if qty <= 0 or step <= 0:
        return 0.0
    precision = max(0, int(round(-math.log10(step)))) if step < 1 else 0
    floored = math.floor(qty / step) * step
    floored = float(f"{floored:.{precision}f}")
    if floored < min_qty:
        return 0.0
    return floored


def ceil_qty(qty: float, step: float, min_qty: float) -> float:
    """Round quantity up to the next valid lot step (for exchange-minimum sizing)."""
    if qty <= 0 or step <= 0:
        return 0.0
    precision = max(0, int(round(-math.log10(step)))) if step < 1 else 0
    steps = math.ceil(qty / step - 1e-12)
    out = float(f"{(steps * step):.{precision}f}")
    if out < min_qty:
        out = float(f"{min_qty:.{precision}f}")
    return out


def min_exchange_qty(entry: float, instrument: dict, *, notional_buffer: float = 0.02) -> float:
    """
    Smallest exchange-legal quantity: max(min_qty, qty needed for min_notional),
    rounded up to qty_step.

    notional_buffer pads the minimum notional so the order is not rejected when the
    price drifts down between sizing and the actual fill.
    """
    if entry <= 0:
        return 0.0
    min_qty = float(instrument["min_qty"])
    step = float(instrument["qty_step"])
    min_notional = float(instrument.get("min_notional") or 0.0)
    need = min_qty
    if min_notional > 0:
        need = max(need, (min_notional * (1.0 + max(0.0, notional_buffer))) / entry)
    return ceil_qty(need, step, min_qty)


def size_qty_risk_with_min_floor(
    *,
    equity: float,
    risk_frac: float,
    entry: float,
    stop: float,
    instrument: dict,
    notional_buffer: float = 0.02,
    max_margin: float | None = None,
    leverage: int = 1,
) -> float:
    """Cash risk = equity × risk_frac, quantity rounded **down** to qty_step.

    If that is below the exchange minimum, **raise to the minimum** (legal order).
    Skip (0) only when margin cannot hold that minimum.
    """
    if equity <= 0 or risk_frac <= 0 or entry <= 0:
        return 0.0
    risk_per_unit = abs(entry - float(stop))
    if risk_per_unit <= 0:
        return 0.0
    step = float(instrument["qty_step"])
    min_qty = float(instrument["min_qty"])
    raw = (equity * float(risk_frac)) / risk_per_unit
    qty_risk = round_qty(raw, step, 0.0)
    qty_min = min_exchange_qty(entry, instrument, notional_buffer=notional_buffer)
    qty = max(qty_risk, qty_min)
    if qty <= 0:
        return 0.0
    if max_margin is not None and leverage > 0:
        cap = (float(max_margin) * float(leverage)) / entry
        cap_floor = round_qty(cap, step, 0.0)
        if cap_floor + 1e-12 < qty_min:
            return 0.0
        qty = min(qty, cap_floor)
        qty = max(qty, qty_min) if qty + 1e-12 >= qty_min else 0.0
    if qty * entry + 1e-12 < float(instrument.get("min_notional") or 0.0):
        qty = qty_min
    if qty < min_qty:
        return 0.0
    return qty
