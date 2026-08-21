"""Research chandelier signals must match the live signals_core copy."""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "deploy" / "tsm_chandelier" / "src"
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from chand.signals_core import build_signal_frame as live_build  # noqa: E402
from strategies.tsm_chandelier.signals import build_signal_frame as research_build  # noqa: E402


def _bars(n: int = 120) -> pd.DataFrame:
    rng = np.random.default_rng(7)
    close = 100.0 + np.cumsum(rng.normal(0, 0.4, n))
    high = close + rng.uniform(0.1, 0.8, n)
    low = close - rng.uniform(0.1, 0.8, n)
    open_ = np.roll(close, 1)
    open_[0] = close[0]
    return pd.DataFrame(
        {
            "ts_ms": np.arange(n, dtype=np.int64) * 3_600_000,
            "open": open_,
            "high": np.maximum(high, np.maximum(open_, close)),
            "low": np.minimum(low, np.minimum(open_, close)),
            "close": close,
            "volume": np.full(n, 1.0),
        }
    )


def test_research_vs_live_core_columns_equal() -> None:
    df = _bars()
    a = research_build(df)
    b = live_build(df)
    for col in ("atr", "stop_price", "target_price"):
        assert np.allclose(a[col].to_numpy(float), b[col].to_numpy(float), equal_nan=True)
    assert np.array_equal(a["long_signal"].to_numpy(bool), b["long_signal"].to_numpy(bool))
    assert np.array_equal(a["short_signal"].to_numpy(bool), b["short_signal"].to_numpy(bool))
