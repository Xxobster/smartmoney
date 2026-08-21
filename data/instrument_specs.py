"""Point-in-time Binance USDT-M perpetual instrument specifications.

Rules are snapshotted with a timestamp. Do not treat values as timeless facts.
Verify against exchange docs/API before live deployment.
"""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict

from paths import INSTRUMENT_SPECS_DIR, ensure_artifact_dirs


@dataclass(frozen=True)
class InstrumentSpec:
    venue: str
    symbol: str
    product_type: str
    tick_size: float
    qty_step: float
    min_qty: float
    min_notional: float
    max_leverage: float
    maintenance_margin_rate: float
    funding_interval_hours: int
    snapshot_utc: str
    source_note: str


# Baseline non-VIP research defaults for Binance USDT-M linear perps.
# Snapshot date: 2026-07-24. Re-fetch before live.
_BASELINE: Dict[str, dict] = {
    "BTCUSDT": dict(
        tick_size=0.1,
        qty_step=0.001,
        min_qty=0.001,
        min_notional=100.0,
        max_leverage=125.0,
        maintenance_margin_rate=0.004,
    ),
    "ETHUSDT": dict(
        tick_size=0.01,
        qty_step=0.001,
        min_qty=0.001,
        min_notional=20.0,
        max_leverage=100.0,
        maintenance_margin_rate=0.005,
    ),
    "SOLUSDT": dict(
        tick_size=0.01,
        qty_step=0.1,
        min_qty=0.1,
        min_notional=5.0,
        max_leverage=50.0,
        maintenance_margin_rate=0.01,
    ),
}


def get_instrument_spec(symbol: str, venue: str = "binance") -> InstrumentSpec:
    key = symbol.upper()
    if key not in _BASELINE:
        # Conservative generic fallback for research proxies
        base = dict(
            tick_size=0.0001,
            qty_step=0.001,
            min_qty=0.001,
            min_notional=5.0,
            max_leverage=20.0,
            maintenance_margin_rate=0.01,
        )
        note = "generic_fallback_research_proxy"
    else:
        base = _BASELINE[key]
        note = "binance_usdtm_baseline_snapshot_2026-07-24"
    return InstrumentSpec(
        venue=venue,
        symbol=key,
        product_type="linear_perpetual",
        funding_interval_hours=8,
        snapshot_utc=datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        source_note=note,
        **base,
    )


def round_price(price: float, tick: float) -> float:
    if tick <= 0:
        return price
    return round(price / tick) * tick


def round_qty(qty: float, step: float) -> float:
    if step <= 0:
        return qty
    return (qty // step) * step


def save_specs(symbols: list[str] | None = None) -> Path:
    ensure_artifact_dirs()
    symbols = symbols or list(_BASELINE.keys())
    payload = {s: asdict(get_instrument_spec(s)) for s in symbols}
    out = INSTRUMENT_SPECS_DIR / "binance_usdtm_specs.json"
    out.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return out


if __name__ == "__main__":
    path = save_specs()
    print(f"Wrote instrument specs -> {path}")
