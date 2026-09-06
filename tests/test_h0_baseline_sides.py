"""Tests for long/short separated hypothesis-0 baseline runs."""

from __future__ import annotations

import pandas as pd

from strategies.common.h0_baseline import (
    H0_DATA_CLASS,
    H0_EVIDENCE_CLASS,
    H0_READINESS,
    LIMIT_OFFSET_FROZEN,
    touch_coverage_frac,
    with_limit_entry,
)
from strategies.common.signal_sides import side_modes_for_source
from tradesim import Signal


def test_h0_is_exploratory_not_an_exam():
    assert H0_EVIDENCE_CLASS == "EXPLORATORY_IN_SAMPLE"
    assert H0_DATA_CLASS == "RESEARCH_PROXY"
    assert H0_READINESS == "LIVE_STOP / RESEARCH_ONLY"


def test_long_only_adds_short_mirror():
    modes = side_modes_for_source("long_only", test_opposite_mirror=True)
    labels = [m[0] for m in modes]
    assert labels == ["long", "short_mirror"]


def test_long_only_without_mirror():
    modes = side_modes_for_source("long_only", test_opposite_mirror=False)
    assert modes == [("long", "long")]


def test_both_sides_no_mirror_labels():
    modes = side_modes_for_source("both", test_opposite_mirror=True)
    labels = [m[0] for m in modes]
    assert labels == ["long", "short"]


def test_touch_coverage_frac_full_and_empty():
    bars = pd.DataFrame({"ts_ms": [0, 3_600_000]})
    touch = pd.DataFrame({"ts_ms": list(range(0, 7_200_000, 60_000))})
    assert touch_coverage_frac(bars, touch, "1h") == 1.0
    assert touch_coverage_frac(bars, pd.DataFrame({"ts_ms": []}), "1h") == 0.0
    late = pd.DataFrame({"ts_ms": [3_600_000 * 100]})
    assert touch_coverage_frac(bars, late, "1h") == 0.0


def test_with_limit_entry_freezes_guide_offset():
    sig = Signal(ts_ms=0, side=1, symbol="BTCUSDT", stop_offset=0.01, target_offset=0.02)
    out = with_limit_entry([sig])
    assert out[0].entry_order == "limit" or getattr(out[0].entry_order, "value", None) == "limit"
    assert out[0].limit_offset == LIMIT_OFFSET_FROZEN
    assert out[0].limit_price is None
    assert sig.entry_order is None
