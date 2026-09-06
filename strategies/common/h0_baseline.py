"""Shared full-history hypothesis-0 runner with separate long / short results.

Full-history H0 is EXPLORATORY_IN_SAMPLE (a public-recipe screen). It is not a
nested outer exam. Do not quote these Profit Factors as Frozen V2.1 proof.

Execution (tradesim EXEC-021): take-profit/stop and resting limits are resolved
on the 1-minute path. A print *before* the limit fill is not a win. Do not treat
a resting-limit fill as the decision-bar open.
"""

from __future__ import annotations

import inspect
from collections.abc import Callable
from dataclasses import replace
from typing import Any, Literal

import numpy as np
import pandas as pd

from tradesim.ensure_source import prefer_botsgeneral_tradesim

prefer_botsgeneral_tradesim()

from data.instrument_specs import get_instrument_spec
from engine.data_loader import load_ohlcv, research_db
from engine.tradesim_adapter import PROJECT_STARTING_EQUITY_USDT, TF_MS, df_to_barseries
from strategies.common.signal_sides import SideMode, side_modes_for_source
from tradesim import InstrumentSpec, Signal, run_backtest
from tradesim.research.defaults import (
    research_costs,
    research_limit_entry_costs,
    research_sim,
    research_sim_limit_entry,
)
from tradesim.venue import InstrumentCache

H0_EVIDENCE_CLASS = "EXPLORATORY_IN_SAMPLE"
H0_DATA_CLASS = "RESEARCH_PROXY"
H0_READINESS = "LIVE_STOP / RESEARCH_ONLY"
# Engine-guide Post-Only example. Frozen. Not a search.
LIMIT_OFFSET_FROZEN = 0.0005
MIN_TOUCH_COVERAGE = 0.95
ExecMode = Literal["taker_market", "exec021_limit"]
_OHLCV_CACHE: dict[tuple[str, str, str], pd.DataFrame] = {}


def _cached_ohlcv(symbol: str, timeframe: str) -> pd.DataFrame:
    key = (str(research_db()), symbol, timeframe)
    hit = _OHLCV_CACHE.get(key)
    if hit is None:
        hit = load_ohlcv(research_db(), symbol, timeframe)
        _OHLCV_CACHE[key] = hit
    return hit


def touch_coverage_frac(bars: pd.DataFrame, touch: pd.DataFrame, timeframe: str) -> float:
    """Fraction of decision bars whose [open, next-open) window has at least one 1m bar."""
    if bars.empty or touch.empty:
        return 0.0
    step = TF_MS[timeframe]
    ts = bars["ts_ms"].to_numpy(np.int64)
    t1 = touch["ts_ms"].to_numpy(np.int64)
    lo = np.searchsorted(t1, ts, side="left")
    hi = np.searchsorted(t1, ts + step, side="left")
    return float(np.mean(hi > lo))


def with_limit_entry(
    signals: list[Signal],
    *,
    offset: float = LIMIT_OFFSET_FROZEN,
) -> list[Signal]:
    return [
        replace(s, entry_order="limit", limit_offset=float(offset), limit_price=None)
        for s in signals
    ]


def _call_build(
    build_signal_frame: Callable[..., pd.DataFrame],
    bars_df: pd.DataFrame,
    symbol: str,
) -> pd.DataFrame:
    kwargs: dict[str, Any] = {}
    params = inspect.signature(build_signal_frame).parameters
    if "htf_1h" in params:
        kwargs["htf_1h"] = _cached_ohlcv(symbol, "1h")
    return build_signal_frame(bars_df, **kwargs)


def _call_to_signals(
    to_tradesim_signals: Callable[..., list[Signal]],
    feat: pd.DataFrame,
    symbol: str,
    max_hold_bars: int,
    side_mode: SideMode,
) -> list[Signal]:
    kwargs: dict[str, Any] = {"max_hold_bars": max_hold_bars}
    if "side_mode" in inspect.signature(to_tradesim_signals).parameters:
        kwargs["side_mode"] = side_mode
    return to_tradesim_signals(feat, symbol, **kwargs)


def metrics_row(m: Any) -> dict[str, Any]:
    sharpe = getattr(m, "sharpe", None)
    return {
        "n_trades": int(m.n_trades),
        "trades_per_month": float(m.trades_per_month),
        "profit_factor": float(m.profit_factor),
        "sharpe_ann": float(sharpe.annualised) if sharpe else 0.0,
        "hac_sharpe_ann": float(sharpe.hac_annualised) if sharpe else 0.0,
        "sortino_ann": float(getattr(m, "sortino_annualised", 0.0) or 0.0),
        "max_drawdown": float(m.max_drawdown_pct),
        "win_rate": float(m.win_rate),
        "net_pnl": float(m.net_pnl),
        "expectancy": float(m.expectancy),
        "payoff_ratio": float(m.payoff_ratio),
        "total_return": float(getattr(m, "total_return", 0.0) or 0.0),
        "total_fees": float(getattr(m, "total_fees", 0.0) or 0.0),
        "exposure": float(getattr(m, "exposure", 0.0) or 0.0),
        "n_exits_tp": int(getattr(m, "n_exits_tp", 0) or 0),
        "n_exits_sl": int(getattr(m, "n_exits_sl", 0) or 0),
        "entry_bar_exits": int(m.entry_bar_exits),
        "entry_bar_exit_rate": float(m.entry_bar_exit_rate),
        "span_days": float(m.span_days),
    }


def local_instrument(symbol: str) -> InstrumentSpec:
    try:
        return InstrumentCache().instrument_spec(
            symbol, refresh_if_missing=False, max_age_ms=10**18
        )
    except Exception:
        snap = get_instrument_spec(symbol)
        return InstrumentSpec(
            symbol=symbol,
            tick_size=snap.tick_size,
            qty_step=snap.qty_step,
            min_qty=snap.min_qty,
            min_notional=snap.min_notional,
            max_leverage=snap.max_leverage,
            maintenance_rate=snap.maintenance_margin_rate,
            source="local_instrument_specs_snapshot",
        )


def run_one_side(
    *,
    symbol: str,
    timeframe: str,
    strategy_id: str,
    strategy_version: str,
    report_side: str,
    side_mode: SideMode,
    build_signal_frame: Callable[[pd.DataFrame], pd.DataFrame],
    to_tradesim_signals: Callable[..., list[Signal]],
    max_hold_bars: int,
    exec_mode: ExecMode = "taker_market",
    print_headline: bool = True,
    require_touch_coverage: bool = True,
) -> dict[str, Any]:
    base = {
        "symbol": symbol,
        "timeframe": timeframe,
        "report_side": report_side,
        "side_mode": side_mode,
        "exec_mode": exec_mode,
        "readiness": H0_READINESS,
        "evidence_class": H0_EVIDENCE_CLASS,
        "data_class": H0_DATA_CLASS,
        "n_trades": 0,
    }
    bars_df = _cached_ohlcv(symbol, timeframe)
    if bars_df.empty:
        return {**base, "status": "no_data"}
    touch = _cached_ohlcv(symbol, "1m")
    cov = touch_coverage_frac(bars_df, touch, timeframe)
    base["touch_coverage"] = cov
    if require_touch_coverage and cov < MIN_TOUCH_COVERAGE:
        return {**base, "status": "incomplete_1m"}
    feat = _call_build(build_signal_frame, bars_df, symbol)
    signals = _call_to_signals(
        to_tradesim_signals, feat, symbol, max_hold_bars, side_mode
    )
    if exec_mode == "exec021_limit":
        signals = with_limit_entry(signals)
        costs = research_limit_entry_costs()
        sim = research_sim_limit_entry(starting_equity=PROJECT_STARTING_EQUITY_USDT)
    else:
        costs = research_costs()
        sim = research_sim(starting_equity=PROJECT_STARTING_EQUITY_USDT)
    if not signals:
        return {**base, "status": "no_signals"}
    bundle = run_backtest(
        strategy_id=f"{strategy_id}_{symbol.lower()}_{timeframe}_{report_side}_{exec_mode}",
        strategy_version=strategy_version,
        bars=df_to_barseries(feat, timeframe, symbol),
        symbol=symbol,
        instrument=local_instrument(symbol),
        signals=signals,
        touch_bars=df_to_barseries(touch, "1m", symbol) if not touch.empty else None,
        starting_equity=PROJECT_STARTING_EQUITY_USDT,
        costs=costs,
        sim=sim,
        plot=False,
        print_headline=print_headline,
        store_path=None,
    )
    return {
        **base,
        **metrics_row(bundle.metrics),
        "status": "ok",
        "headline": bundle.headline,
    }


def run_h0_matrix(
    *,
    strategy_id: str,
    strategy_version: str,
    symbols: tuple[str, ...],
    timeframes: tuple[str, ...],
    holds: dict[str, int],
    build_signal_frame: Callable[[pd.DataFrame], pd.DataFrame],
    to_tradesim_signals: Callable[..., list[Signal]],
    source_side: str = "long_only",
    test_opposite_mirror: bool = True,
    exec_mode: ExecMode = "taker_market",
    print_headline: bool = True,
    require_touch_coverage: bool = True,
) -> list[dict[str, Any]]:
    """Run baseline backtests; long-only sources also get a separate short_mirror run."""
    results: list[dict[str, Any]] = []
    modes = side_modes_for_source(
        source_side,
        test_opposite_mirror=test_opposite_mirror,
    )
    for symbol in symbols:
        for timeframe in timeframes:
            hold = holds.get(timeframe, 48)
            for report_side, side_mode in modes:
                results.append(
                    run_one_side(
                        symbol=symbol,
                        timeframe=timeframe,
                        strategy_id=strategy_id,
                        strategy_version=strategy_version,
                        report_side=report_side,
                        side_mode=side_mode,
                        build_signal_frame=build_signal_frame,
                        to_tradesim_signals=to_tradesim_signals,
                        max_hold_bars=hold,
                        exec_mode=exec_mode,
                        print_headline=print_headline,
                        require_touch_coverage=require_touch_coverage,
                    )
                )
    return results
