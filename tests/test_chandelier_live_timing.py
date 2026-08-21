"""Live chandelier entry-timing guards (no exchange calls)."""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "deploy" / "tsm_chandelier" / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from chand.live.binance_fallback import merge_closed_bars, series_gaps  # noqa: E402
from chand.live.state import LiveState  # noqa: E402


def test_stale_skip_does_not_overwrite_fill(tmp_path: Path) -> None:
    st = LiveState(tmp_path / "live.sqlite")
    st.mark_entry_handled(
        "BTCUSDT",
        1_786_460_400_000,
        "short",
        {"entry_ts_ms": 1_786_460_400_000, "qty": 0.001},
    )
    st.mark_entry_handled(
        "BTCUSDT",
        1_786_460_400_000,
        "short",
        {"skipped": "stale_entry", "delay_sec": 900},
    )
    detail = st.handled_detail("BTCUSDT", 1_786_460_400_000)
    assert detail is not None
    assert detail.get("skipped") is None
    assert detail.get("qty") == 0.001


def test_merge_closed_bars_prefers_fallback_row() -> None:
    base = pd.DataFrame(
        {
            "ts_ms": [1_000, 2_000],
            "open": [1.0, 2.0],
            "high": [1.1, 2.1],
            "low": [0.9, 1.9],
            "close": [1.05, 2.05],
            "volume": [10.0, 11.0],
        }
    )
    extra = pd.DataFrame(
        {
            "ts_ms": [2_000, 3_000],
            "open": [2.0, 3.0],
            "high": [2.2, 3.2],
            "low": [1.8, 2.8],
            "close": [2.1, 3.1],
            "volume": [12.0, 13.0],
        }
    )
    out = merge_closed_bars(base, extra)
    assert list(out["ts_ms"]) == [1_000, 2_000, 3_000]
    assert float(out.loc[out["ts_ms"] == 2_000, "close"].iloc[0]) == 2.1


def test_series_gaps_counts_missing_hours() -> None:
    ts = [0, 3_600_000, 14_400_000]
    gaps = series_gaps(ts, 3_600_000)
    assert gaps == [(3_600_000, 14_400_000, 2)]
