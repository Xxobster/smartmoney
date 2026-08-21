"""Confluence scoring and trade-signal assembly from SMC primitives."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np
import pandas as pd

from smc.fvg import compute_fvg
from smc.liquidity import compute_liquidity
from smc.order_blocks import compute_order_blocks
from smc.premium_discount import compute_premium_discount
from smc.structure import compute_structure
from smc.volume import compute_volume


@dataclass
class ConfluenceConfig:
    swing_left: int = 3
    swing_right: int = 3
    bos_requires_close: bool = True
    fvg_model: str = "wick"
    require_liquidity_sweep: bool = True
    require_bos_or_choch: bool = True
    require_fvg: bool = True
    require_order_block: bool = False
    require_premium_discount: bool = True
    min_confluence_count: int = 3
    volume_confirm_lookback: int = 5
    volume_confirm_mult: float = 1.2
    event_lookback: int = 24  # bars for recent sweep/structure memory
    # Session filter (UTC hour of bar open). none = no filter.
    # killzones = London open 07-10 or NY open 12-16 UTC (classic ICT windows).
    # london_ny = continuous 07-21 UTC trading day.
    session_mode: str = "none"
    # Require raw gate true for (confirm_bars+1) consecutive bars before entry.
    confirm_bars: int = 0


def session_mask(ts_ms: np.ndarray, mode: str) -> np.ndarray:
    """UTC session mask for bar open timestamps (vectorized)."""
    mode = (mode or "none").strip().lower()
    hours = ((np.asarray(ts_ms, dtype=np.int64) // 3_600_000) % 24).astype(np.int64)
    if mode in ("", "none", "all"):
        return np.ones(hours.shape, dtype=bool)
    if mode == "killzones":
        return ((hours >= 7) & (hours < 10)) | ((hours >= 12) & (hours < 16))
    if mode in ("london_ny", "london_ny_window"):
        return (hours >= 7) & (hours < 21)
    if mode == "london":
        return (hours >= 7) & (hours < 16)
    if mode == "ny":
        return (hours >= 12) & (hours < 21)
    raise ValueError(f"Unknown session_mode={mode!r}")


def build_feature_frame(df: pd.DataFrame, cfg: ConfluenceConfig) -> pd.DataFrame:
    """Compute all SMC features on a single-timeframe OHLCV frame (causal)."""
    assert df["ts_ms"].is_monotonic_increasing
    structure = compute_structure(
        df, left=cfg.swing_left, right=cfg.swing_right, bos_requires_close=cfg.bos_requires_close
    )
    liq = compute_liquidity(
        df,
        structure["swing_high"].to_numpy(),
        structure["swing_low"].to_numpy(),
        structure["last_swing_high"].to_numpy(),
        structure["last_swing_low"].to_numpy(),
    )
    vol = compute_volume(df, cfg.volume_confirm_lookback, cfg.volume_confirm_mult)
    fvg = compute_fvg(df, model=cfg.fvg_model)
    ob = compute_order_blocks(df, atr=vol["atr"].to_numpy())
    pd_ = compute_premium_discount(
        df,
        structure["last_swing_high"].to_numpy(),
        structure["last_swing_low"].to_numpy(),
        fvg["active_bull_fvg_top"].to_numpy(),
        fvg["active_bull_fvg_bot"].to_numpy(),
    )

    out = pd.concat(
        [
            df.reset_index(drop=True),
            structure.reset_index(drop=True),
            liq.reset_index(drop=True),
            vol.reset_index(drop=True),
            fvg.reset_index(drop=True),
            ob.reset_index(drop=True),
            pd_.reset_index(drop=True),
        ],
        axis=1,
    )
    return out


def _recent(flag: pd.Series, lookback: int) -> pd.Series:
    """True if flag fired on this bar or any of the prior `lookback` bars (causal)."""
    return flag.astype(int).rolling(lookback + 1, min_periods=1).max().astype(bool)


def score_confluence(feat: pd.DataFrame, cfg: ConfluenceConfig) -> pd.DataFrame:
    """Produce long/short confluence counts and entry flags.

    Events are sequenced in time (sweep / structure first, then zone revisits),
    so liquidity and structure flags use a causal lookback window rather than
    requiring every condition on the exact same bar.
    """
    event_lb = max(int(getattr(cfg, "event_lookback", 24)), 1)

    # Long ingredients
    long_parts = {
        "sweep": _recent(feat["bull_sweep"].astype(bool), event_lb),
        "structure": _recent((feat["bull_bos"] | feat["bull_choch"]).astype(bool), event_lb),
        "fvg": feat["price_in_bull_fvg"].astype(bool),
        "ob": feat["price_in_bull_ob"].astype(bool),
        "pd": feat["in_discount"].astype(bool),
        "volume": feat["volume_confirm"].astype(bool),
        "htf_bias": (feat["bias"] >= 0).astype(bool),  # replaced by HTF join later
    }
    short_parts = {
        "sweep": _recent(feat["bear_sweep"].astype(bool), event_lb),
        "structure": _recent((feat["bear_bos"] | feat["bear_choch"]).astype(bool), event_lb),
        "fvg": feat["price_in_bear_fvg"].astype(bool),
        "ob": feat["price_in_bear_ob"].astype(bool),
        "pd": feat["in_premium"].astype(bool),
        "volume": feat["volume_confirm"].astype(bool),
        "htf_bias": (feat["bias"] <= 0).astype(bool),
    }

    long_count = (
        long_parts["sweep"].astype(int)
        + long_parts["structure"].astype(int)
        + long_parts["fvg"].astype(int)
        + long_parts["ob"].astype(int)
        + long_parts["pd"].astype(int)
        + long_parts["volume"].astype(int)
    )
    short_count = (
        short_parts["sweep"].astype(int)
        + short_parts["structure"].astype(int)
        + short_parts["fvg"].astype(int)
        + short_parts["ob"].astype(int)
        + short_parts["pd"].astype(int)
        + short_parts["volume"].astype(int)
    )

    def _gate(parts: dict[str, Any], side: str) -> pd.Series:
        ok = pd.Series(True, index=feat.index)
        if cfg.require_liquidity_sweep:
            ok &= parts["sweep"]
        if cfg.require_bos_or_choch:
            ok &= parts["structure"]
        if cfg.require_fvg:
            ok &= parts["fvg"]
        if cfg.require_order_block:
            ok &= parts["ob"]
        if cfg.require_premium_discount:
            ok &= parts["pd"]
        # Never against bias on this TF
        ok &= parts["htf_bias"]
        # Hard rejects
        ok &= ~feat["vsa_weak_move"].astype(bool)
        count = long_count if side == "long" else short_count
        ok &= count >= cfg.min_confluence_count
        # Entry confirmation: volume or rejection-like bar preferred
        ok &= parts["volume"] | parts["fvg"] | parts["ob"]
        return ok

    long_signal = _gate(long_parts, "long")
    short_signal = _gate(short_parts, "short")

    sess = session_mask(feat["ts_ms"].to_numpy(dtype=np.int64), getattr(cfg, "session_mode", "none"))
    long_signal = long_signal & sess
    short_signal = short_signal & sess

    confirm = int(getattr(cfg, "confirm_bars", 0) or 0)
    if confirm > 0:
        win = confirm + 1
        long_signal = long_signal.astype(int).rolling(win, min_periods=win).min().fillna(0).astype(bool)
        short_signal = short_signal.astype(int).rolling(win, min_periods=win).min().fillna(0).astype(bool)

    # Carry last sweep extreme forward for stop placement after lookback events
    sweep_ext = feat["sweep_extreme"].copy()
    # Prefer most recent bullish extreme for longs / bearish for shorts when signal fires
    bull_ext = feat["sweep_extreme"].where(feat["bull_sweep"]).ffill()
    bear_ext = feat["sweep_extreme"].where(feat["bear_sweep"]).ffill()
    sweep_for_trade = sweep_ext.copy()
    sweep_for_trade = sweep_for_trade.where(~long_signal, bull_ext)
    sweep_for_trade = sweep_for_trade.where(~short_signal, bear_ext)

    return pd.DataFrame(
        {
            "long_confluence": long_count,
            "short_confluence": short_count,
            "long_signal": long_signal,
            "short_signal": short_signal,
            "long_sweep": long_parts["sweep"],
            "short_sweep": short_parts["sweep"],
            "sweep_extreme": sweep_for_trade,
            "atr": feat["atr"],
            "pd_q50": feat["pd_q50"],
            "pd_q75": feat["pd_q75"],
            "pd_q25": feat["pd_q25"],
            "last_swing_high": feat["last_swing_high"],
            "last_swing_low": feat["last_swing_low"],
        }
    )
