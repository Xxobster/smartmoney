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
