"""tsm_chandelier live bot: 1h ATR-band + Chandelier stop on Bybit via botsgeneral candles."""

from __future__ import annotations

import json
import logging
import time
from dataclasses import asdict
from pathlib import Path
from typing import Any

from chand.margin import DEFAULT_CONTRACT, leverage_from_stop, stop_beyond_liquidation
from chand.live.bybit_client import BybitClient, BybitCredentials, format_price, format_qty
from chand.live import shared_candles
from chand.live.binance_fallback import fetch_closed_klines, merge_closed_bars, series_gaps
from chand.live.schedule import sleep_sec_for_tf
from chand.live.signals import TF_MS, LiveSignal, actionable_signal, generate_live_signals
from chand.live.sizing import min_exchange_qty, round_qty, size_qty_risk_with_min_floor
from chand.live.state import LiveState

log = logging.getLogger(__name__)

ROOT = Path(__file__).resolve().parents[3]
DEFAULT_PACK = ROOT / "configs" / "live_btc_eth_sol_1h_xxobster6.json"


def load_pack(path: Path | str) -> dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def position_idx_for_side(side: str) -> int:
    return 1 if side == "long" else 2


class ChandLiveBot:
    def __init__(
        self,
        symbol: str,
        *,
        pack_path: Path | str = DEFAULT_PACK,
        account: str | None = None,
        state_db: Path | str | None = None,
        keys_path: Path | str | None = None,
        dry_run: bool | None = None,
    ):
        self.pack = load_pack(pack_path)
        self.symbol = symbol.upper()
        self.timeframe = str(self.pack.get("timeframe", "1h"))
        self.exchange = str(self.pack.get("candles_exchange") or "binance")
        self.costs = self.pack["costs"]
        self.poll_sec = int(self.pack.get("poll_sec", 60))
        self.dense_poll_sec = float(self.pack.get("dense_poll_sec", 5))
        self.idle_poll_sec = float(self.pack.get("idle_poll_sec", self.poll_sec))
        self.pre_close_sec = float(self.pack.get("pre_close_sec", 45))
        self.post_close_sec = float(self.pack.get("post_close_sec", 180))
        self.min_bars = int(self.pack.get("min_bars", 80))
        self.max_hold = int(self.pack.get("strategy", {}).get("max_hold_bars", 36))
        self.use_min_size = bool(self.pack.get("use_min_size", True))
        self.dry_run = bool(self.pack.get("dry_run", False) if dry_run is None else dry_run)
        acct = account or self.pack.get("account") or "Xxobster6"
        keys = Path(keys_path) if keys_path else ROOT / "config" / "api_keys.json"
        self.client = BybitClient(BybitCredentials.from_account(acct, path=keys))
        state_path = Path(state_db) if state_db else ROOT / "data" / "live" / "tsm_chandelier_live.sqlite"
        self.state = LiveState(state_path)
        self.instrument = self.client.get_instrument_info(self.symbol)
        self.notional_buffer = float(self.pack.get("min_notional_buffer", 0.02))
        self.snapshot_interval_sec = float(self.pack.get("snapshot_interval_sec", 300))
        self.bar_settle_sec = float(self.pack.get("bar_settle_sec", 20))
        self.max_entry_delay_sec = float(self.pack.get("max_entry_delay_sec", 600))
        self.account_margin_mode = "UNKNOWN"
        self._wait_logged = False
        self._last_seen_closed_ts: int | None = None
        self._last_snapshot_ms: int | None = None

    def bootstrap(self) -> None:
        db = shared_candles.shared_db_path()
        log.info(
            "Bootstrap %s exchange=%s tf=%s min_size=%s dry_run=%s shared_db=%s",
            self.symbol,
            self.exchange,
            self.timeframe,
            self.use_min_size,
            self.dry_run,
            db,
        )
        try:
            self.client.switch_hedge_mode(self.symbol)
        except Exception:
            log.exception("Hedge mode switch failed for %s (continuing)", self.symbol)

        try:
            mode = self.client.get_account_mode()
            self.account_margin_mode = str(mode.get("margin_mode") or "UNKNOWN")
        except Exception:
            log.exception("%s could not read account margin mode", self.symbol)
        if self.account_margin_mode != "ISOLATED_MARGIN":
            log.warning(
                "%s live margin mode is %s (cross) — liquidation/margin parity is APPROXIMATE",
                self.symbol,
                self.account_margin_mode,
            )

        n = shared_candles.candle_count(self.symbol, self.timeframe, exchange=self.exchange)
        ok, last, reason = shared_candles.candles_fresh(
            self.symbol, self.timeframe, exchange=self.exchange
        )
        if not ok:
            log.warning("Waiting for botsgeneral candles: %s (bars=%s)", reason, n)
        else:
            log.info("Shared candles ready last_ts_ms=%s bars=%s", last, n)

        self._adopt_existing_position()
        self.state.log_event(
            self.symbol,
            "bootstrap",
            {
                "bars": n,
                "candles_ok": ok,
                "reason": reason,
                "account_margin_mode": self.account_margin_mode,
                "use_min_size": self.use_min_size,
                "instrument": self.instrument,
                "pack_id": self.pack.get("pack_id"),
            },
        )

    def _adopt_existing_position(self) -> None:
        pos = self._open_exchange_position()
        if pos is None or self.state.get_open_trade(self.symbol):
            return
        side = "long" if str(pos.get("side")) == "Buy" else "short"
        entry_ts = int(pos.get("createdTime") or pos.get("updatedTime") or self._now_ms())
        trade = {
            "symbol": self.symbol,
            "side": side,
            "entry_ts_ms": entry_ts,
            "entry_price": float(pos.get("avgPrice") or 0),
            "stop_price": float(pos.get("stopLoss") or 0),
            "target_price": float(pos.get("takeProfit") or 0),
            "qty": float(pos.get("size") or 0),
            "leverage": int(float(pos.get("leverage") or 1)),
            "position_idx": int(pos.get("positionIdx") or 0),
            "pattern": "adopted_unknown",
            "detail": {"adopted": True, "position": pos},
        }
        log.warning("%s adopting untracked exchange position side=%s qty=%s", self.symbol, side, trade["qty"])
        self.state.set_open_trade(trade)
        self.state.log_event(self.symbol, "position_adopted", trade)

    def _open_exchange_position(self) -> dict | None:
        for p in self.client.get_positions(self.symbol):
            if float(p.get("size", 0) or 0) > 0:
                return p
        return None

    def _sync_closed(self) -> None:
        local = self.state.get_open_trade(self.symbol)
        if not local:
            return
        if self._open_exchange_position() is not None:
            return
        log.info("%s position closed on exchange — recording realized result", self.symbol)
        self._record_realized(local)
        self.state.log_event(self.symbol, "position_closed", local)
        self.state.clear_open_trade(self.symbol)

    def _record_realized(self, local: dict[str, Any]) -> None:
        try:
            start = max(0, int(local.get("entry_ts_ms") or 0) - 6 * 3_600_000)
            rows = self.client.get_closed_pnl(self.symbol, limit=50, start_ms=start or None)
            n = self.state.record_closed_trades(self.symbol, rows, planned=local)
            log.info("%s recorded %s closed-trade row(s)", self.symbol, n)
        except Exception:
            log.exception("%s failed to record closed profit and loss", self.symbol)
        try:
            fnd = self.client.get_funding_settlements(self.symbol, limit=50)
            self.state.record_funding(self.symbol, fnd)
        except Exception:
            log.exception("%s failed to record funding settlements", self.symbol)

    def _snapshot(self, now_ms: int, *, force: bool = False) -> None:
        if not force and self._last_snapshot_ms is not None:
            if now_ms - self._last_snapshot_ms < int(self.snapshot_interval_sec * 1000):
                return
        try:
            wallet = self.client.get_wallet_snapshot()
            pos = self._open_exchange_position()
            self.state.snapshot_equity(self.symbol, now_ms, wallet, pos)
            self._last_snapshot_ms = now_ms
        except Exception:
            log.exception("%s equity snapshot failed", self.symbol)

    def _equity_base(self) -> float:
        wallet = self.client.get_wallet_balance_usdt()
        if not self.use_min_size:
            return max(0.0, float(wallet))
        cap = float(self.costs["starting_equity_per_pair"])
        return max(0.0, min(wallet, cap))

    def _size_order(self, sig: LiveSignal, entry: float) -> tuple[float, int, float]:
        if entry <= 0:
            return 0.0, 1, 0.0
        equity = self._equity_base()
        lev = leverage_from_stop(
            entry,
            float(sig.stop_price),
            symbol=self.symbol,
            contract=DEFAULT_CONTRACT,
            exchange_max=int(self.instrument["max_leverage"]),
        )
        if not stop_beyond_liquidation(sig.side, entry, float(sig.stop_price), lev):
            log.error(
                "%s refuse entry: SL not safer than approx liquidation entry=%s stop=%s lev=%s",
                self.symbol,
                entry,
                sig.stop_price,
                lev,
            )
            return 0.0, lev, equity

        if self.use_min_size:
            qty = min_exchange_qty(entry, self.instrument, notional_buffer=self.notional_buffer)
            if qty <= 0:
                return 0.0, lev, equity
            return qty, lev, equity

        max_margin = equity * float(DEFAULT_CONTRACT.max_margin_utilization)
        qty = size_qty_risk_with_min_floor(
            equity=equity,
            risk_frac=float(self.costs["risk_frac"]),
            entry=entry,
            stop=float(sig.stop_price),
            instrument=self.instrument,
            notional_buffer=self.notional_buffer,
            max_margin=max_margin,
            leverage=lev,
        )
        return qty, lev, equity

    def _place_maker_exits(
        self,
        *,
        side: str,
        qty: float,
        position_idx: int,
        stop_price: float,
        target_price: float,
    ) -> None:
        """Bot-owned reduce-only Post-Only take-profit + stop-limit. Not exchange stop-market."""
        tick = float(self.instrument["tick_size"])
        step = float(self.instrument["qty_step"])
        floored = round_qty(qty, step, 0.0)
        if floored <= 0:
            raise RuntimeError(f"{self.symbol} maker-exit qty floors to 0")
        qty_str = format_qty(floored, step)
        sl = format_price(float(stop_price), tick)
        tp = format_price(float(target_price), tick)
        try:
            self.client.clear_trading_stop(self.symbol, position_idx)
        except Exception:
            log.exception("%s clear_trading_stop (best-effort)", self.symbol)
        self.client.place_maker_take_profit(
            self.symbol,
            side=side,
            qty=qty_str,
            price=tp,
            position_idx=position_idx,
        )
        self.client.place_maker_stop_limit(
            self.symbol,
            side=side,
            qty=qty_str,
            stop_price=sl,
            position_idx=position_idx,
        )
        self.state.log_event(
            self.symbol,
            "maker_exits_placed",
            {"side": side, "qty": qty_str, "stop": sl, "target": tp, "position_idx": position_idx},
        )

    def _ensure_maker_exits(self) -> None:
        local = self.state.get_open_trade(self.symbol)
        if not local or not self._open_exchange_position():
            return
        if self.client.has_reduce_only_working_order(self.symbol, int(local["position_idx"])):
            return
        try:
            self._place_maker_exits(
                side=str(local["side"]),
                qty=float(local.get("qty") or 0),
                position_idx=int(local["position_idx"]),
                stop_price=float(local["stop_price"]),
                target_price=float(local["target_price"]),
            )
        except Exception:
            log.exception("%s maker-exit ensure failed", self.symbol)

    def _maybe_time_exit(self, last_closed_ts_ms: int) -> None:
        local = self.state.get_open_trade(self.symbol)
        if not local:
            return
        step = TF_MS.get(self.timeframe, 3_600_000)
        held_bars = int((last_closed_ts_ms - int(local["entry_ts_ms"])) // step)
        if held_bars < self.max_hold:
            return
        pos = self._open_exchange_position()
        if pos is None:
            self.state.clear_open_trade(self.symbol)
            return
        side = local["side"]
        exit_side = "Sell" if side == "long" else "Buy"
        qty = format_qty(float(pos.get("size") or local["qty"]), self.instrument["qty_step"])
        idx = int(local["position_idx"])
        log.warning("%s max_hold=%s reached — market flatten qty=%s", self.symbol, self.max_hold, qty)
        if self.dry_run:
            self.state.log_event(self.symbol, "dry_run_time_exit", {"held_bars": held_bars, "qty": qty})
            return
        self.client.place_market_order(
            self.symbol, exit_side, qty, position_idx=idx, reduce_only=True
        )
        self.state.log_event(self.symbol, "time_exit", {"held_bars": held_bars, "qty": qty, **local})
        time.sleep(2)
        self._record_realized(local)
        self.state.clear_open_trade(self.symbol)
        self._snapshot(self._now_ms(), force=True)

    def _enter(self, sig: LiveSignal, *, now_ms: int | None = None, last_closed_ts_ms: int | None = None) -> None:
        if self.state.entry_handled(self.symbol, sig.entry_ts_ms):
            return
        if self.state.get_open_trade(self.symbol) or self._open_exchange_position():
            log.info("%s skip entry — already in position", self.symbol)
            self.state.mark_entry_handled(self.symbol, sig.entry_ts_ms, sig.side, {"skipped": "in_position"})
            return

        try:
            last = self.client.get_ticker_last(self.symbol)
        except Exception:
            last = float(sig.entry_ref_price)
        entry_est = last if last > 0 else float(sig.entry_ref_price)
        qty, lev, equity = self._size_order(sig, entry_est)
        if qty <= 0:
            log.warning("%s qty=0 after sizing (equity_base=%.2f)", self.symbol, equity)
            self.state.mark_entry_handled(self.symbol, sig.entry_ts_ms, sig.side, {"skipped": "qty0"})
            return

        idx = position_idx_for_side(sig.side)
        side = "Buy" if sig.side == "long" else "Sell"
        sl = format_price(float(sig.stop_price), self.instrument["tick_size"])
        tp = format_price(float(sig.target_price), self.instrument["tick_size"])
        qty_str = format_qty(qty, self.instrument["qty_step"])
        decision_ms = now_ms if now_ms is not None else self._now_ms()
        delay_sec = (decision_ms - int(sig.entry_ts_ms)) / 1000.0
        step = TF_MS.get(self.timeframe, 3_600_000)
        expected_closed = (decision_ms // step) * step - step
        closed_ts = int(last_closed_ts_ms) if last_closed_ts_ms is not None else None
        # Seconds after the decision bar closed until we act (candle availability lag).
        candle_lag_sec = (
            (decision_ms - (closed_ts + step)) / 1000.0 if closed_ts is not None else None
        )
        candle_behind_sec = (
            (expected_closed - closed_ts) / 1000.0
            if closed_ts is not None
            else None
        )
        detail = {
            "side": sig.side,
            "entry_ts_ms": sig.entry_ts_ms,
            "signal_ts_ms": sig.signal_ts_ms,
            "last_closed_ts_ms": last_closed_ts_ms,
            "expected_closed_ts_ms": expected_closed,
            "decision_ts_ms": decision_ms,
            "decision_delay_sec": delay_sec,
            "candle_lag_sec": candle_lag_sec,
            "candle_behind_sec": candle_behind_sec,
            "entry_est": entry_est,
            "qty": qty,
            "leverage": lev,
            "equity_base": equity,
            "wallet_margin_mode": self.account_margin_mode,
            "stop": sl,
            "target": tp,
            "pattern": sig.pattern,
            "min_size_mode": self.use_min_size,
            "dry_run": self.dry_run,
        }
        log.info(
            "%s ENTRY signal side=%s qty=%s lev=%sx sl=%s tp=%s "
            "decision_delay=%.1fs candle_lag=%.1fs candle_behind=%.1fs est_px=%s",
            self.symbol,
            sig.side,
            qty_str,
            lev,
            sl,
            tp,
            delay_sec,
            candle_lag_sec if candle_lag_sec is not None else -1.0,
            candle_behind_sec if candle_behind_sec is not None else -1.0,
            entry_est,
        )
        self.state.log_event(self.symbol, "entry_timing", detail)
        if self.dry_run:
            self.state.mark_entry_handled(self.symbol, sig.entry_ts_ms, sig.side, detail)
            self.state.log_event(self.symbol, "dry_run_entry", detail)
            return

        self.client.set_leverage(self.symbol, lev, lev)
        self.client.place_market_order(
            self.symbol,
            side,
            qty_str,
            position_idx=idx,
        )
        fill = self.client.wait_for_position_fill(self.symbol, idx)
        fill_px = float(fill["avgPrice"])
        lev_fill = leverage_from_stop(
            fill_px,
            float(sig.stop_price),
            symbol=self.symbol,
            contract=DEFAULT_CONTRACT,
            exchange_max=int(self.instrument["max_leverage"]),
        )
        if lev_fill != lev:
            log.info("%s adjust leverage after fill %sx -> %sx fill=%s", self.symbol, lev, lev_fill, fill_px)
            try:
                self.client.set_leverage(self.symbol, lev_fill, lev_fill)
            except Exception:
                log.exception("%s post-fill set_leverage failed", self.symbol)
            lev = lev_fill
        if not stop_beyond_liquidation(sig.side, fill_px, float(sig.stop_price), lev):
            log.error("%s CRITICAL: fill leaves SL unsafe — flattening", self.symbol)
            exit_side = "Sell" if sig.side == "long" else "Buy"
            self.client.place_market_order(
                self.symbol,
                exit_side,
                format_qty(fill["size"], self.instrument["qty_step"]),
                position_idx=idx,
                reduce_only=True,
            )
            self.state.mark_entry_handled(
                self.symbol, sig.entry_ts_ms, sig.side, {**detail, "flattened": "liq_unsafe"}
            )
            return
        try:
            self._place_maker_exits(
                side=sig.side,
                qty=float(fill["size"]),
                position_idx=idx,
                stop_price=float(sig.stop_price),
                target_price=float(sig.target_price),
            )
        except Exception:
            log.exception("%s maker TP/SL place failed after fill — flattening", self.symbol)
            exit_side = "Sell" if sig.side == "long" else "Buy"
            self.client.place_market_order(
                self.symbol,
                exit_side,
                format_qty(fill["size"], self.instrument["qty_step"]),
                position_idx=idx,
                reduce_only=True,
            )
            self.state.mark_entry_handled(
                self.symbol, sig.entry_ts_ms, sig.side, {**detail, "flattened": "maker_exit_failed"}
            )
            return
        trade = {
            "symbol": self.symbol,
            "side": sig.side,
            "entry_ts_ms": sig.entry_ts_ms,
            "entry_price": fill_px,
            "stop_price": float(sig.stop_price),
            "target_price": float(sig.target_price),
            "qty": fill["size"],
            "leverage": lev,
            "position_idx": idx,
            "pattern": sig.pattern,
            "detail": {**detail, "fill": fill, "signal": asdict(sig), "lev_after_fill": lev},
        }
        self.state.set_open_trade(trade)
        self.state.mark_entry_handled(self.symbol, sig.entry_ts_ms, sig.side, detail)
        self.state.log_event(self.symbol, "entry_filled", trade)
        self._snapshot(self._now_ms(), force=True)

    def cycle(self) -> None:
        now_ms = self._now_ms()
        ok, last, reason = shared_candles.candles_fresh(
            self.symbol, self.timeframe, exchange=self.exchange
        )
        n = shared_candles.candle_count(self.symbol, self.timeframe, exchange=self.exchange)
        step = TF_MS.get(self.timeframe, 3_600_000)
        expected_closed = (now_ms // step) * step - step
        df_all = shared_candles.load_candles(self.symbol, self.timeframe, exchange=self.exchange)
        if (not ok or last is None or int(last) < expected_closed) and self.exchange == "binance":
            extra = fetch_closed_klines(
                self.symbol,
                self.timeframe,
                start_ms=expected_closed,
                limit=6,
                now_ms=now_ms,
            )
            if not extra.empty:
                df_all = merge_closed_bars(df_all, extra)
                last = int(df_all["ts_ms"].iloc[-1])
                ok = last >= expected_closed
                n = len(df_all)
                reason = "binance_rest_fallback"
                log.info(
                    "%s filled just-closed bar from Binance REST last=%s expected=%s",
                    self.symbol,
                    last,
                    expected_closed,
                )
        if not ok or n < self.min_bars:
            if not self._wait_logged:
                log.warning("%s waiting for candles: %s bars=%s", self.symbol, reason, n)
                self._wait_logged = True
            self._snapshot(now_ms)
            return
        if self._wait_logged:
            log.info("%s candles ready — trading armed bars=%s last=%s", self.symbol, n, last)
            self._wait_logged = False

        if df_all.empty:
            return
        df = df_all[df_all["ts_ms"] + step + int(self.bar_settle_sec * 1000) <= now_ms]

        self._sync_closed()
        if df.empty or len(df) < self.min_bars:
            self._snapshot(now_ms)
            return

        lookback = df.tail(max(self.min_bars, 80))
        gaps = series_gaps(lookback["ts_ms"].to_numpy(), step)
        if gaps:
            log.warning(
                "%s lookback has %s 1h gap(s) in last %s bars (ATR/EMA50 may diverge from backtest)",
                self.symbol,
                len(gaps),
                len(lookback),
            )

        last_closed = int(df["ts_ms"].iloc[-1])
        self._maybe_time_exit(last_closed)
        self._ensure_maker_exits()
        self._snapshot(now_ms)

        if self._last_seen_closed_ts != last_closed:
            log.info(
                "%s completed bar ts=%s usable_after_close=%.1fs complete=%s",
                self.symbol,
                last_closed,
                (now_ms - (last_closed + step)) / 1000.0,
                len(df),
            )
        self._last_seen_closed_ts = last_closed

        signals = generate_live_signals(df, timeframe=self.timeframe)
        sig = actionable_signal(
            signals,
            last_closed_ts_ms=last_closed,
            timeframe=self.timeframe,
            now_ms=now_ms,
        )
        if sig is None:
            return
        if self.state.entry_handled(self.symbol, sig.entry_ts_ms):
            return
        delay_sec = (now_ms - int(sig.entry_ts_ms)) / 1000.0
        candle_lag_sec = (now_ms - (last_closed + step)) / 1000.0
        candle_behind_sec = (expected_closed - last_closed) / 1000.0
        if delay_sec > self.max_entry_delay_sec:
            log.warning(
                "%s skip %s signal — %.0fs late (limit %.0fs) "
                "candle_lag=%.1fs candle_behind=%.1fs",
                self.symbol,
                sig.side,
                delay_sec,
                self.max_entry_delay_sec,
                candle_lag_sec,
                candle_behind_sec,
            )
            skip_detail = {
                "skipped": "stale_entry",
                "delay_sec": delay_sec,
                "decision_delay_sec": delay_sec,
                "candle_lag_sec": candle_lag_sec,
                "candle_behind_sec": candle_behind_sec,
                "last_closed_ts_ms": last_closed,
                "expected_closed_ts_ms": expected_closed,
                "signal": asdict(sig),
            }
            self.state.mark_entry_handled(
                self.symbol,
                sig.entry_ts_ms,
                sig.side,
                skip_detail,
            )
            self.state.log_event(self.symbol, "entry_timing", skip_detail)
            return
        self._enter(sig, now_ms=now_ms, last_closed_ts_ms=last_closed)

    def _now_ms(self) -> int:
        try:
            return int(self.client.get_server_time_ms())
        except Exception:
            log.exception("%s server time failed — falling back to local UTC", self.symbol)
            return int(time.time() * 1000)

    def _next_sleep_sec(self) -> float:
        now = self._now_ms()
        step = TF_MS.get(self.timeframe, 3_600_000)
        if self._last_seen_closed_ts is None:
            return float(self.dense_poll_sec)
        return sleep_sec_for_tf(
            now,
            step_ms=step,
            last_closed_ts_ms=self._last_seen_closed_ts,
            dense_poll_sec=self.dense_poll_sec,
            idle_poll_sec=self.idle_poll_sec,
            pre_close_sec=self.pre_close_sec,
            post_close_sec=self.post_close_sec,
        )

    def run(self) -> None:
        self.bootstrap()
        log.info(
            "Live loop start %s dense=%ss idle=%ss around 1h close",
            self.symbol,
            self.dense_poll_sec,
            self.idle_poll_sec,
        )
        while True:
            try:
                self.cycle()
            except Exception:
                log.exception("%s cycle error", self.symbol)
            time.sleep(max(1.0, self._next_sleep_sec()))
