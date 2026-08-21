"""Event-driven backtest with next-executable fills, fees, funding, mark liquidation."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional

import numpy as np
import pandas as pd

from data.instrument_specs import get_instrument_spec, round_price, round_qty


@dataclass
class BacktestConfig:
    initial_equity: float = 10_000.0
    risk_fraction: float = 0.005
    leverage: float = 3.0
    taker_fee: float = 0.0005
    maker_fee: float = 0.0002
    slippage_bps: float = 1.0
    all_taker: bool = True
    target_rr: float = 3.0
    use_pd_targets: bool = True
    stop_beyond_sweep_atr_mult: float = 0.1
    max_hold_bars: int = 96
    maintenance_margin_rate: float = 0.004
    funding_enabled: bool = False


@dataclass
class Trade:
    symbol: str
    side: int  # 1 long, -1 short
    entry_ts: int
    entry_px: float
    qty: float
    stop: float
    target: float
    exit_ts: Optional[int] = None
    exit_px: Optional[float] = None
    pnl: float = 0.0
    fees: float = 0.0
    funding: float = 0.0
    reason: str = ""
    liquidated: bool = False


@dataclass
class BacktestResult:
    trades: List[Trade] = field(default_factory=list)
    equity_curve: pd.DataFrame = field(default_factory=pd.DataFrame)
    skipped_orders: int = 0
    liquidations: int = 0
    funding_pnl: float = 0.0
    fees_paid: float = 0.0
    config: Optional[BacktestConfig] = None


def _fee_rate(cfg: BacktestConfig) -> float:
    return cfg.taker_fee if cfg.all_taker else cfg.maker_fee


def _slip(side: int, px: float, bps: float, is_entry: bool) -> float:
    # Adverse slippage
    sign = side if is_entry else -side
    return px * (1.0 + sign * bps * 1e-4)


def run_backtest(
    signals: pd.DataFrame,
    cfg: BacktestConfig,
    symbol: str = "BTCUSDT",
    funding: Optional[pd.DataFrame] = None,
    mark: Optional[pd.DataFrame] = None,
) -> BacktestResult:
    """Signals must include open/high/low/close/ts_ms and long_signal/short_signal.

    Entry: next bar open after signal bar close (causality).
    TP/SL checked on subsequent bars using high/low; mark used for liquidation if provided.
    """
    if signals.empty:
        return BacktestResult(config=cfg)

    spec = get_instrument_spec(symbol)
    cfg.maintenance_margin_rate = spec.maintenance_margin_rate

    ts = signals["ts_ms"].to_numpy(np.int64)
    o = signals["open"].to_numpy(float)
    h = signals["high"].to_numpy(float)
    l = signals["low"].to_numpy(float)
    c = signals["close"].to_numpy(float)
    long_sig = signals["long_signal"].to_numpy(bool)
    short_sig = signals["short_signal"].to_numpy(bool)
    atr = signals["atr"].to_numpy(float) if "atr" in signals.columns else np.full(len(signals), np.nan)
    sweep_ext = (
        signals["sweep_extreme"].to_numpy(float)
        if "sweep_extreme" in signals.columns
        else np.full(len(signals), np.nan)
    )
    pd_q50 = signals["pd_q50"].to_numpy(float) if "pd_q50" in signals.columns else np.full(len(signals), np.nan)
    pd_q75 = signals["pd_q75"].to_numpy(float) if "pd_q75" in signals.columns else np.full(len(signals), np.nan)
    pd_q25 = signals["pd_q25"].to_numpy(float) if "pd_q25" in signals.columns else np.full(len(signals), np.nan)

    mark_close = None
    if mark is not None and not mark.empty:
        m = pd.merge_asof(
            pd.DataFrame({"ts_ms": ts}),
            mark[["ts_ms", "close"]].sort_values("ts_ms").rename(columns={"close": "mark"}),
            on="ts_ms",
            direction="backward",
        )
        mark_close = m["mark"].to_numpy(float)
    else:
        mark_close = c.copy()

    funding_map = {}
    if cfg.funding_enabled and funding is not None and not funding.empty:
        funding_map = dict(
            zip(funding["funding_time_ms"].astype(np.int64), funding["funding_rate"].astype(float))
        )

    equity = cfg.initial_equity
    position: Optional[Trade] = None
    trades: List[Trade] = []
    skipped = 0
    liquidations = 0
    fees_paid = 0.0
    funding_pnl = 0.0
    eq_rows = []
    pending_side = 0
    pending_stop = np.nan
    pending_target = np.nan
    pending_from = -1

    fee_r = _fee_rate(cfg)

    for i in range(len(signals) - 1):
        # Funding settlement while open
        if position is not None and funding_map:
            t = int(ts[i])
            # Funding times align near 00/08/16 UTC; match exact keys in map within bar
            for ft, fr in list(funding_map.items()):
                if ts[i] <= ft < ts[i + 1]:
                    # Long pays when funding > 0
                    pay = position.side * position.qty * mark_close[i] * fr
                    position.funding -= pay
                    funding_pnl -= pay
                    equity -= pay
                    del funding_map[ft]

        # Manage open position on this bar (after entry bar)
        if position is not None:
            # Liquidation check on mark
            notional = position.qty * mark_close[i]
            margin = notional / max(cfg.leverage, 1e-9)
            upnl = position.side * position.qty * (mark_close[i] - position.entry_px)
            # Simple isolated: liquidated when equity cushion vs maintenance breached
            if margin + upnl <= notional * cfg.maintenance_margin_rate:
                exit_px = round_price(_slip(position.side, mark_close[i], cfg.slippage_bps, False), spec.tick_size)
                fee = abs(position.qty * exit_px * fee_r)
                pnl = position.side * position.qty * (exit_px - position.entry_px) - fee + position.funding
                # Subtract entry fee already accounted; funding already applied
                equity += position.side * position.qty * (exit_px - position.entry_px) - fee
                fees_paid += fee
                position.exit_ts = int(ts[i])
                position.exit_px = exit_px
                position.pnl = pnl
                position.fees += fee
                position.reason = "liquidation"
                position.liquidated = True
                trades.append(position)
                position = None
                liquidations += 1
            else:
                hit_sl = (position.side == 1 and l[i] <= position.stop) or (
                    position.side == -1 and h[i] >= position.stop
                )
                hit_tp = (position.side == 1 and h[i] >= position.target) or (
                    position.side == -1 and l[i] <= position.target
                )
                timed = (i - pending_from) >= cfg.max_hold_bars if pending_from >= 0 else False
                # Same-bar ambiguity: adverse first
                reason = None
                exit_px = None
                if hit_sl and hit_tp:
                    exit_px = position.stop
                    reason = "sl_before_tp_ambiguous"
                elif hit_sl:
                    exit_px = position.stop
                    reason = "stop"
                elif hit_tp:
                    exit_px = position.target
                    reason = "target"
                elif timed:
                    exit_px = c[i]
                    reason = "max_hold"
                if reason is not None:
                    exit_px = round_price(_slip(position.side, float(exit_px), cfg.slippage_bps, False), spec.tick_size)
                    fee = abs(position.qty * exit_px * fee_r)
                    pnl = position.side * position.qty * (exit_px - position.entry_px) - fee
                    # Entry fee was charged at entry; include in trade.fees
                    equity += position.side * position.qty * (exit_px - position.entry_px) - fee
                    fees_paid += fee
                    position.exit_ts = int(ts[i])
                    position.exit_px = exit_px
                    position.pnl = pnl + position.funding
                    position.fees += fee
                    position.reason = reason
                    trades.append(position)
                    position = None

        # Place pending entry from prior signal onto this bar's open (i is fill bar)
        if position is None and pending_side != 0:
            entry_px = round_price(_slip(pending_side, o[i], cfg.slippage_bps, True), spec.tick_size)
            stop = round_price(pending_stop, spec.tick_size)
            target = round_price(pending_target, spec.tick_size)
            risk_per_unit = abs(entry_px - stop)
            if risk_per_unit <= 0 or np.isnan(risk_per_unit):
                skipped += 1
                pending_side = 0
            else:
                risk_cash = equity * cfg.risk_fraction
                qty = risk_cash / risk_per_unit
                qty = round_qty(qty, spec.qty_step)
                notional = qty * entry_px
                if qty < spec.min_qty or notional < spec.min_notional:
                    skipped += 1
                    pending_side = 0
                else:
                    # Leverage / margin check
                    margin_needed = notional / max(cfg.leverage, 1e-9)
                    if margin_needed > equity * 0.60:
                        skipped += 1
                        pending_side = 0
                    else:
                        fee = abs(qty * entry_px * fee_r)
                        equity -= fee
                        fees_paid += fee
                        position = Trade(
                            symbol=symbol,
                            side=pending_side,
                            entry_ts=int(ts[i]),
                            entry_px=entry_px,
                            qty=qty,
                            stop=stop,
                            target=target,
                            fees=fee,
                        )
                        pending_from = i
                        pending_side = 0

        # New signals on bar i become pending for bar i+1 (known after close of i)
        if position is None and pending_side == 0:
            side = 0
            if long_sig[i] and not short_sig[i]:
                side = 1
            elif short_sig[i] and not long_sig[i]:
                side = -1
            if side != 0:
                a = atr[i] if not np.isnan(atr[i]) else (h[i] - l[i])
                if side == 1:
                    extreme = sweep_ext[i] if not np.isnan(sweep_ext[i]) else l[i]
                    stop = extreme - cfg.stop_beyond_sweep_atr_mult * a
                    if cfg.use_pd_targets and not np.isnan(pd_q50[i]):
                        target = pd_q75[i] if not np.isnan(pd_q75[i]) else pd_q50[i]
                    else:
                        target = c[i] + cfg.target_rr * (c[i] - stop)
                else:
                    extreme = sweep_ext[i] if not np.isnan(sweep_ext[i]) else h[i]
                    stop = extreme + cfg.stop_beyond_sweep_atr_mult * a
                    if cfg.use_pd_targets and not np.isnan(pd_q50[i]):
                        target = pd_q25[i] if not np.isnan(pd_q25[i]) else pd_q50[i]
                    else:
                        target = c[i] - cfg.target_rr * (stop - c[i])
                pending_side = side
                pending_stop = stop
                pending_target = target

        mtm = equity
        if position is not None:
            mtm += position.side * position.qty * (mark_close[i] - position.entry_px)
        eq_rows.append({"ts_ms": int(ts[i]), "equity": mtm, "wallet": equity})

    # Force flat at end
    if position is not None:
        i = len(signals) - 1
        exit_px = round_price(_slip(position.side, c[i], cfg.slippage_bps, False), spec.tick_size)
        fee = abs(position.qty * exit_px * fee_r)
        equity += position.side * position.qty * (exit_px - position.entry_px) - fee
        fees_paid += fee
        position.exit_ts = int(ts[i])
        position.exit_px = exit_px
        position.pnl = position.side * position.qty * (exit_px - position.entry_px) - fee + position.funding
        position.fees += fee
        position.reason = "eod_flat"
        trades.append(position)

    eq = pd.DataFrame(eq_rows)
    return BacktestResult(
        trades=trades,
        equity_curve=eq,
        skipped_orders=skipped,
        liquidations=liquidations,
        funding_pnl=funding_pnl,
        fees_paid=fees_paid,
        config=cfg,
    )
