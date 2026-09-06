# Take-profit / stop-loss MUST be maker — the bot places the orders

**MUST.** Read this before modelling fees or attaching Bybit take-profit / stop-loss.

## The myth

“The take-profit and stop-loss are maker because we trade small size, so they fill anyway.”

**That is false.** Fee class is **maker vs taker**, not size. A **stop-market** (Bybit attached Take Profit / Stop Loss with order type Market) **takes** liquidity when it fires. You pay **taker 0.055%**. Small quantity does not change that.

## What the live bot MUST do

The bot **owns** the exit orders. Do **not** rely on Bybit position Take Profit / Stop Loss Market attachments.

1. **Take-profit:** the bot places a **reduce-only Post-Only limit** at the take-profit price (correct tick, correct quantity, round **down** to the quantity step, then raise to exchange **minimum** if needed so the order is legal). If it **rests**, the fill is **maker 0.02%** at the limit.
2. **Stop-loss:** the bot places a **reduce-only stop-limit** at the stop price (conditional; **not** a resting sell below the market on a long — that would cross immediately and be **taker**, and would close the trade at once). Maker **0.02%** only if that fill **actually rests**.
3. **Heartbeat:** if the stop-limit is missing, cancelled, or price is through the stop and the limit did not fill, **market-flatten** (taker, last resort). Max-hold flatten is also taker.
4. **Quantity / price format:** venue tick and lot step. **Round down** when the exact value is not on the grid. Never send a quantity the exchange will reject for format.

## What you MUST NOT do

- Call an attached Bybit **Market** take-profit / stop-loss “maker”.
- Charge maker fees in a backtest for **stop-market** exits.
- Place a long’s stop as a naked sell **limit below the bid** (that is a crossing taker, not a stop).
- Assume a candle **touch** is a maker fill.

## Backtest

- Product path that matches this live spec: maker **0.02%** on resting take-profit / stop-limit legs; fill at the **limit** when touched (`EXEC-005` / `EXEC-021`).
- **Stress** path remains all-taker **0.055%**. A maker path cannot rescue a failing taker stress without fill evidence.
- Last-resort market flatten, max-hold, liquidation: **taker**.

Identifier: live bots that still attach stop-**market** are **not** on this spec. Fix the bot; do not relabel the fee.
