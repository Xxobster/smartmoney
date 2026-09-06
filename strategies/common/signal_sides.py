"""Long / short side modes for hypothesis-0 backtests from video-sourced rules."""

from __future__ import annotations

from typing import Literal

SideMode = Literal["long", "short", "short_mirror", "long_mirror"]
SourceSidePolicy = Literal["long_only", "short_only", "both"]

SIDE_LABELS: dict[SideMode, str] = {
    "long": "long",
    "short": "short",
    "short_mirror": "short_mirror",
    "long_mirror": "long_mirror",
}


def side_modes_for_source(
    source_side: SourceSidePolicy,
    *,
    test_opposite_mirror: bool = True,
) -> list[tuple[str, SideMode]]:
    """Return (report_label, signal_mode) pairs for separate backtest runs.

    When a YouTube recipe is long-only, we still run a mirrored short test and
    report long vs short_mirror separately (not pooled).
    """
    if source_side == "long_only":
        modes: list[tuple[str, SideMode]] = [("long", "long")]
        if test_opposite_mirror:
            modes.append(("short_mirror", "short_mirror"))
        return modes
    if source_side == "short_only":
        modes = [("short", "short")]
        if test_opposite_mirror:
            modes.append(("long_mirror", "long_mirror"))
        return modes
    return [("long", "long"), ("short", "short")]
