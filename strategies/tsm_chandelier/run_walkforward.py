"""Fixed-H0 nested outer OOS for chandelier 1h (preregistered YAML)."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from research.tsm_fixed_h0_walkforward import main_chandelier

if __name__ == "__main__":
    main_chandelier()
