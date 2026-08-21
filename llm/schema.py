"""Pydantic StrategySpec schema for LLM proposals and Optuna trials."""
from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator

from smc.confluence import ConfluenceConfig


def _norm_tf(v: Any) -> str:
    return str(v).strip().lower()


def _norm_bool(v: Any) -> bool:
    if isinstance(v, bool):
        return v
    if isinstance(v, str):
        return v.strip().lower() in {"1", "true", "yes", "y"}
    return bool(v)


class StrategySpec(BaseModel):
    name: str = "SMC_Confluence_Retrace"
    bias_timeframe: Literal["1d", "4h", "1h"] = "4h"
    structure_timeframe: Literal["4h", "1h", "15m"] = "1h"
    execution_timeframe: Literal["15m", "5m"] = "15m"
    swing_left: int = Field(3, ge=2, le=8)
    swing_right: int = Field(3, ge=2, le=8)
    bos_requires_close: bool = True
    fvg_model: Literal["wick", "body"] = "wick"
    require_liquidity_sweep: bool = True
    require_bos_or_choch: bool = True
    require_fvg: bool = True
    require_order_block: bool = False
    require_premium_discount: bool = True
    min_confluence_count: int = Field(3, ge=2, le=6)
    volume_confirm_lookback: int = Field(5, ge=2, le=20)
    volume_confirm_mult: float = Field(1.2, ge=1.0, le=3.0)
    stop_beyond_sweep_atr_mult: float = Field(0.1, ge=0.0, le=1.0)
    target_rr: float = Field(3.0, ge=1.0, le=6.0)
    use_pd_targets: bool = True
    max_hold_bars: int = Field(96, ge=12, le=500)
    risk_fraction: float = Field(0.005, ge=0.001, le=0.02)
    event_lookback: int = Field(24, ge=8, le=96)
    session_mode: Literal["none", "killzones", "london_ny", "london", "ny"] = "none"
    confirm_bars: int = Field(0, ge=0, le=5)
    rationale: str = ""
    economic_justification: str = ""

    @field_validator(
        "bias_timeframe",
        "structure_timeframe",
        "execution_timeframe",
        "fvg_model",
        "session_mode",
        mode="before",
    )
    @classmethod
    def lowercase_enums(cls, v: Any) -> Any:
        return _norm_tf(v) if v is not None else v

    @field_validator(
        "bos_requires_close",
        "require_liquidity_sweep",
        "require_bos_or_choch",
        "require_fvg",
        "require_order_block",
        "require_premium_discount",
        "use_pd_targets",
        mode="before",
    )
    @classmethod
    def coerce_bools(cls, v: Any) -> Any:
        return _norm_bool(v)

    def to_confluence_config(self) -> ConfluenceConfig:
        return ConfluenceConfig(
            swing_left=self.swing_left,
            swing_right=self.swing_right,
            bos_requires_close=self.bos_requires_close,
            fvg_model=self.fvg_model,
            require_liquidity_sweep=self.require_liquidity_sweep,
            require_bos_or_choch=self.require_bos_or_choch,
            require_fvg=self.require_fvg,
            require_order_block=self.require_order_block,
            require_premium_discount=self.require_premium_discount,
            min_confluence_count=self.min_confluence_count,
            volume_confirm_lookback=self.volume_confirm_lookback,
            volume_confirm_mult=self.volume_confirm_mult,
            event_lookback=int(getattr(self, "event_lookback", 24) or 24),
            session_mode=str(getattr(self, "session_mode", "none") or "none"),
            confirm_bars=int(getattr(self, "confirm_bars", 0) or 0),
        )

    def to_params_dict(self) -> dict[str, Any]:
        return self.model_dump()

    @classmethod
    def from_logical_seed(cls, seed: dict) -> "StrategySpec":
        return cls(**{k: v for k, v in seed.items() if k in cls.model_fields})


STRATEGY_SPEC_JSON_SCHEMA = StrategySpec.model_json_schema()
