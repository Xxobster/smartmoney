"""Bybit unified REST client for TSM-VPA live trading."""

from __future__ import annotations

import json
import math
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from pybit.unified_trading import HTTP

PROJECT_ROOT = Path(__file__).resolve().parents[3]


@dataclass
class BybitCredentials:
    api_key: str
    api_secret: str
    testnet: bool = False

    @classmethod
    def from_account(cls, account: str, path: Path | None = None) -> "BybitCredentials":
        p = path or PROJECT_ROOT / "config" / "api_keys.json"
        data = json.loads(p.read_text(encoding="utf-8"))
        key = account if account in data else account.lower()
        if key not in data:
            # case-insensitive fallback
            lower_map = {k.lower(): k for k in data}
            if account.lower() not in lower_map:
                raise KeyError(f"Account {account!r} not in {p}")
            key = lower_map[account.lower()]
        row = data[key]
        return cls(
            api_key=row["api_key"],
            api_secret=row["api_secret"],
            testnet=bool(row.get("testnet", False)),
        )


class BybitClient:
    def __init__(self, creds: BybitCredentials):
        self.creds = creds
        self.http = HTTP(
            testnet=creds.testnet,
            api_key=creds.api_key,
            api_secret=creds.api_secret,
        )

    def _ok(self, resp: dict) -> dict:
        if resp.get("retCode", -1) != 0:
            raise RuntimeError(f"Bybit Application Programming Interface (API) error: {resp.get('retMsg')} ({resp})")
        return resp.get("result", {})

    def get_wallet_balance_usdt(self) -> float:
        r = self.http.get_wallet_balance(accountType="UNIFIED", coin="USDT")
        result = self._ok(r)
        for acct in result.get("list", []):
            for c in acct.get("coin", []):
                if c.get("coin") == "USDT":
                    return float(c.get("walletBalance", 0) or 0)
        return 0.0

    def get_wallet_snapshot(self) -> dict[str, float | None]:
        r = self.http.get_wallet_balance(accountType="UNIFIED", coin="USDT")
        result = self._ok(r)
        out: dict[str, float | None] = {
            "wallet_balance": None,
            "total_equity": None,
            "available": None,
        }
        for acct in result.get("list", []):
            eq = acct.get("totalEquity")
            avail = acct.get("totalAvailableBalance")
            if eq not in (None, ""):
                out["total_equity"] = float(eq)
            if avail not in (None, ""):
                out["available"] = float(avail)
            for c in acct.get("coin", []):
                if c.get("coin") == "USDT":
                    out["wallet_balance"] = float(c.get("walletBalance") or 0)
        return out

    def get_instrument_info(self, symbol: str) -> dict[str, Any]:
        r = self.http.get_instruments_info(category="linear", symbol=symbol)
        items = self._ok(r).get("list", [])
        if not items:
            raise RuntimeError(f"No instrument info for {symbol}")
        info = items[0]
        lot = info.get("lotSizeFilter", {})
        price = info.get("priceFilter", {})
        lev = info.get("leverageFilter", {})
        return {
            "min_qty": float(lot.get("minOrderQty", "0.001")),
            "qty_step": float(lot.get("qtyStep", "0.001")),
            "min_notional": float(lot.get("minNotionalValue", "5") or 5),
            "tick_size": float(price.get("tickSize", "0.01")),
            "max_leverage": float(lev.get("maxLeverage", "50")),
        }

    def switch_isolated(self, symbol: str, leverage: int = 1) -> None:
        """Best-effort isolated mode. Unified Trading Account (UTA) often rejects this."""
        lev = str(max(1, int(leverage)))
        try:
            r = self.http.switch_margin_mode(
                category="linear",
                symbol=symbol,
                tradeMode=1,
                buyLeverage=lev,
                sellLeverage=lev,
            )
            code = r.get("retCode", -1)
            msg = str(r.get("retMsg", "")).lower()
            if code != 0 and "not modified" not in msg and code not in (110026, 110043, 100028):
                raise RuntimeError(f"switch_margin_mode: {r.get('retMsg')}")
        except Exception as e:
            text = str(e).lower()
            if any(x in text for x in ("not modified", "110026", "110043", "100028", "unified account is forbidden")):
                return
            raise

    def switch_hedge_mode(self, symbol: str) -> None:
        try:
            r = self.http.switch_position_mode(category="linear", symbol=symbol, mode=3)
            code = r.get("retCode", -1)
            msg = str(r.get("retMsg", "")).lower()
            if code != 0 and "not modified" not in msg and code not in (110025, 110043, 100028):
                raise RuntimeError(f"switch_position_mode: {r.get('retMsg')}")
        except Exception as e:
            text = str(e).lower()
            if any(x in text for x in ("not modified", "110025", "110043", "100028", "unified account is forbidden")):
                return
            raise

    def set_leverage(self, symbol: str, buy_leverage: int, sell_leverage: int) -> None:
        for lev in (buy_leverage, sell_leverage):
            try:
                r = self.http.set_leverage(
                    category="linear",
                    symbol=symbol,
                    buyLeverage=str(lev),
                    sellLeverage=str(lev),
                )
                if r.get("retCode", -1) != 0:
                    msg = r.get("retMsg", "")
                    if "110043" in str(r) or "leverage not modified" in msg.lower():
                        continue
                    raise RuntimeError(f"Bybit set_leverage: {msg}")
            except Exception as e:
                if "110043" in str(e) or "leverage not modified" in str(e).lower():
                    continue
                raise

    def get_positions(self, symbol: str) -> list[dict]:
        r = self.http.get_positions(category="linear", symbol=symbol)
        return self._ok(r).get("list", [])

    def wait_for_position_fill(
        self,
        symbol: str,
        position_idx: int,
        *,
        timeout_sec: float = 20.0,
        poll_sec: float = 0.25,
    ) -> dict[str, float]:
        deadline = time.time() + timeout_sec
        while time.time() < deadline:
            for p in self.get_positions(symbol):
                if int(p.get("positionIdx", 0)) != position_idx:
                    continue
                size = float(p.get("size", 0) or 0)
                entry = float(p.get("avgPrice", 0) or 0)
                if size > 0 and entry > 0:
                    return {"size": size, "avgPrice": entry}
            time.sleep(poll_sec)
        raise RuntimeError(f"Timed out waiting for fill {symbol} idx={position_idx}")

    def place_market_order(
        self,
        symbol: str,
        side: str,
        qty: str,
        position_idx: int,
        take_profit: str | None = None,
        stop_loss: str | None = None,
        reduce_only: bool = False,
    ) -> dict:
        kwargs: dict[str, Any] = {
            "category": "linear",
            "symbol": symbol,
            "side": side,
            "orderType": "Market",
            "qty": qty,
            "positionIdx": position_idx,
            "reduceOnly": reduce_only,
            "timeInForce": "GTC",
        }
        # Backtest resolves exits against Last-price candles, so trigger on LastPrice.
        if take_profit:
            kwargs["takeProfit"] = take_profit
            kwargs["tpTriggerBy"] = "LastPrice"
        if stop_loss:
            kwargs["stopLoss"] = stop_loss
            kwargs["slTriggerBy"] = "LastPrice"
        r = self.http.place_order(**kwargs)
        return self._ok(r)

    def set_trading_stop(
        self,
        symbol: str,
        position_idx: int,
        stop_loss: str | None = None,
        take_profit: str | None = None,
    ) -> dict:
        kwargs: dict[str, Any] = {
            "category": "linear",
            "symbol": symbol,
            "positionIdx": position_idx,
        }
        if stop_loss is not None:
            kwargs["stopLoss"] = stop_loss
            kwargs["slTriggerBy"] = "LastPrice"
        if take_profit is not None:
            kwargs["takeProfit"] = take_profit
            kwargs["tpTriggerBy"] = "LastPrice"
        r = self.http.set_trading_stop(**kwargs)
        return self._ok(r)

    def get_ticker_last(self, symbol: str) -> float:
        r = self.http.get_tickers(category="linear", symbol=symbol)
        items = self._ok(r).get("list", [])
        if not items:
            raise RuntimeError(f"No ticker for {symbol}")
        return float(items[0].get("lastPrice") or 0)

    def get_account_mode(self) -> dict[str, Any]:
        """Unified Trading Account (UTA) margin mode, needed because isolated may be forbidden."""
        r = self.http.get_account_info()
        res = self._ok(r)
        return {
            "margin_mode": res.get("marginMode"),
            "unified_margin_status": res.get("unifiedMarginStatus"),
        }

    def get_closed_pnl(self, symbol: str, *, limit: int = 50, start_ms: int | None = None) -> list[dict]:
        kwargs: dict[str, Any] = {"category": "linear", "symbol": symbol, "limit": limit}
        if start_ms is not None:
            kwargs["startTime"] = int(start_ms)
        r = self.http.get_closed_pnl(**kwargs)
        return self._ok(r).get("list", [])

    def get_executions(self, symbol: str, *, limit: int = 50, start_ms: int | None = None) -> list[dict]:
        kwargs: dict[str, Any] = {"category": "linear", "symbol": symbol, "limit": limit}
        if start_ms is not None:
            kwargs["startTime"] = int(start_ms)
        r = self.http.get_executions(**kwargs)
        return self._ok(r).get("list", [])

    def get_funding_settlements(self, symbol: str, *, limit: int = 50) -> list[dict]:
        r = self.http.get_transaction_log(
            accountType="UNIFIED",
            category="linear",
            currency="USDT",
            type="SETTLEMENT",
            symbol=symbol,
            limit=limit,
        )
        return self._ok(r).get("list", [])

    def get_server_time_ms(self) -> int:
        """Bybit exchange server time in milliseconds (UTC)."""
        r = self.http.get_server_time()
        result = self._ok(r)
        # Prefer nano/second fields when present; fall back to top-level time.
        if "timeSecond" in result:
            return int(result["timeSecond"]) * 1000
        if isinstance(r.get("time"), (int, float)):
            return int(r["time"])
        import time as _time

        return int(_time.time() * 1000)



def round_qty(qty: float, step: float, min_qty: float) -> float:
    from .sizing import round_qty as _round_qty

    return _round_qty(qty, step, min_qty)


def ceil_qty(qty: float, step: float, min_qty: float) -> float:
    from .sizing import ceil_qty as _ceil_qty

    return _ceil_qty(qty, step, min_qty)


def min_exchange_qty(entry: float, instrument: dict) -> float:
    from .sizing import min_exchange_qty as _min_exchange_qty

    return _min_exchange_qty(entry, instrument)


def format_price(price: float, tick: float) -> str:
    if tick <= 0:
        return f"{price:.8f}".rstrip("0").rstrip(".")
    precision = max(0, int(round(-math.log10(tick)))) if tick < 1 else 0
    rounded = round(round(price / tick) * tick, precision)
    return f"{rounded:.{precision}f}"


def format_qty(qty: float, step: float) -> str:
    if step <= 0:
        return f"{qty:.8f}".rstrip("0").rstrip(".")
    precision = max(0, int(round(-math.log10(step)))) if step < 1 else 0
    return f"{qty:.{precision}f}"
