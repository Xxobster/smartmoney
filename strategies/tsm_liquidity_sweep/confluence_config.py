"""Video-faithful confluence defaults for The Secret Mindset liquidity sweep H0."""

from __future__ import annotations

from smc.confluence import ConfluenceConfig

# H0: prioritize liquidity sweep + structure; do not require FVG/OB on the same bar.
# Matches video emphasis on stop-hunt reclaim over indicator stacks.
TSM_LIQUIDITY_H0 = ConfluenceConfig(
    swing_left=3,
    swing_right=3,
    bos_requires_close=True,
    fvg_model="wick",
    require_liquidity_sweep=True,
    require_bos_or_choch=False,  # video: sweep+reversal can be enough; structure is filter via bias
    require_fvg=False,
    require_order_block=False,
    require_premium_discount=False,
    min_confluence_count=1,  # sweep gate is hard via require_liquidity_sweep
    volume_confirm_lookback=5,
    volume_confirm_mult=1.2,
    event_lookback=12,
    session_mode="none",
    confirm_bars=0,
)

STRATEGY_ID = "tsm_liquidity_sweep"
STRATEGY_VERSION = "0.1.0"
SOURCE_VIDEO_ID = "9P7uB4nBfyA"
DEFAULT_LTF = "15m"
DEFAULT_HTF = "1h"
DEFAULT_SYMBOLS = ("BTCUSDT", "ETHUSDT")
DEFAULT_TARGET_RR = 2.0
DEFAULT_STOP_ATR_MULT = 0.15
