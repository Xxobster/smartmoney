"""Entry guard (2026-11-10): do not send the market entry when the price has already run into the planned stop.

Incident 2026-11-08 22:00 UTC (BTCUSDT, SOLUSDT shorts): the hourly bar opened at 74 097 and spiked to 74 344 within a minute;
the market order filled at 74 345.3, 13 points ABOVE the planned stop 74 332.4, so the position was stopped out at once for
-5.4 R instead of -1 R. The guard reads the latest price right before the order and skips the entry when

* the price already crossed the planned stop (short: price >= stop, long: price <= stop), or
* the distance left to the stop is below ``MIN_STOP_DISTANCE_FRAC`` (25 %) of the planned distance ``|entry_ref - stop|``, or
* the price could not be read (fail closed).

Pure function, no I/O, unit-tested in tests/test_chandelier_entry_guard.py.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

MIN_STOP_DISTANCE_FRAC = 0.25

REASON_OK = "ok"
REASON_CROSSED = "price_crossed_stop"
REASON_TOO_CLOSE = "stop_distance_below_min_fraction"
REASON_PRICE_FAIL = "price_read_failed"
REASON_BAD_PLAN = "bad_plan"


@dataclass(frozen=True)
class GuardVerdict:
    ok: bool
    reason: str
    price: float
    stop: float
    entry_ref: float
    planned_distance: float
    remaining_distance: float
    remaining_frac: float

    def as_dict(self) -> dict:
        return {
            "ok": self.ok,
            "reason": self.reason,
            "price": self.price,
            "stop": self.stop,
            "entry_ref": self.entry_ref,
            "planned_distance": self.planned_distance,
            "remaining_distance": self.remaining_distance,
            "remaining_frac": self.remaining_frac,
            "min_frac": MIN_STOP_DISTANCE_FRAC,
        }


def evaluate_entry_guard(
    *,
    side: str,
    price: float | None,
    stop: float,
    entry_ref: float,
    min_frac: float = MIN_STOP_DISTANCE_FRAC,
) -> GuardVerdict:
    """``side`` is ``"long"`` or ``"short"``. ``price`` None / NaN / <= 0 means the read failed."""
    nan = float("nan")
    try:
        px = float(price) if price is not None else nan
    except (TypeError, ValueError):
        px = nan
    stop_f, ref_f = float(stop), float(entry_ref)
    planned = abs(ref_f - stop_f)
    if not math.isfinite(px) or px <= 0:
        return GuardVerdict(False, REASON_PRICE_FAIL, nan, stop_f, ref_f, planned, nan, nan)
    if not math.isfinite(planned) or planned <= 0:
        return GuardVerdict(False, REASON_BAD_PLAN, px, stop_f, ref_f, planned, nan, nan)
    remaining = (stop_f - px) if side == "short" else (px - stop_f)
    frac = remaining / planned
    if remaining <= 0:
        return GuardVerdict(False, REASON_CROSSED, px, stop_f, ref_f, planned, remaining, frac)
    if frac < float(min_frac):
        return GuardVerdict(False, REASON_TOO_CLOSE, px, stop_f, ref_f, planned, remaining, frac)
    return GuardVerdict(True, REASON_OK, px, stop_f, ref_f, planned, remaining, frac)
