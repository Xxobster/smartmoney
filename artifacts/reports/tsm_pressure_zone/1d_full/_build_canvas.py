"""Build Cursor canvas with full metrics + all pressure-zone 1d trades."""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
CANVAS = Path(
    r"C:\Users\xxobs\.cursor\projects\d-projects-smartmoney\canvases\tsm-pressure-zone-1d.canvas.tsx"
)

btc_m = json.loads((ROOT / "BTCUSDT" / "metrics_full.json").read_text(encoding="utf-8"))
eth_m = json.loads((ROOT / "ETHUSDT" / "metrics_full.json").read_text(encoding="utf-8"))
btc_t = json.loads((ROOT / "BTCUSDT" / "trades_all.json").read_text(encoding="utf-8"))
eth_t = json.loads((ROOT / "ETHUSDT" / "trades_all.json").read_text(encoding="utf-8"))


def slim(t: dict) -> dict:
    return {
        "id": t["trade_id"],
        "sym": t["symbol"],
        "side": t["side"],
        "entry": t["entry_ts_utc"][:10],
        "exit": t["exit_ts_utc"][:10],
        "ep": round(float(t["entry_price"]), 2),
        "xp": round(float(t["exit_price"]), 2),
        "pnl": round(float(t["realized_pnl"]), 4),
        "fees": round(float(t["fees"]), 4),
        "reason": t["exit_reason"],
        "hold": int(t["hold_bars"]),
        "mae": round(float(t["mae"]), 4),
        "mfe": round(float(t["mfe"]), 4),
    }


def metric_block(m: dict) -> dict:
    sh = m["sharpe"]
    return {
        "n_trades": m["n_trades"],
        "n_longs": m["n_longs"],
        "n_shorts": m["n_shorts"],
        "trades_per_month": round(m["trades_per_month"], 2),
        "span_days": round(m["span_days"], 1),
        "net_pnl": round(m["net_pnl"], 4),
        "ending_equity": round(m["ending_equity"], 2),
        "return_on_invested_pct": round(100 * m["return_on_invested"], 3),
        "wallet_return_pct": round(100 * m["total_return"], 3),
        "profit_factor": round(m["profit_factor"], 4),
        "win_rate_pct": round(100 * m["win_rate"], 2),
        "win_rate_ci": [
            round(100 * m["win_rate_ci_low"], 2),
            round(100 * m["win_rate_ci_high"], 2),
        ],
        "expectancy": round(m["expectancy"], 4),
        "payoff_ratio": round(m["payoff_ratio"], 3),
        "avg_win": round(m["avg_win"], 4),
        "avg_loss": round(m["avg_loss"], 4),
        "best_trade": round(m["best_trade"], 4),
        "worst_trade": round(m["worst_trade"], 4),
        "sharpe_ann": round(sh["annualised"], 4),
        "hac_sharpe_ann": round(sh["hac_annualised"], 4),
        "sortino_ann": round(m["sortino_annualised"], 4),
        "max_dd_pct": round(100 * m["max_drawdown_pct"], 3),
        "max_dd_days": round(m["max_drawdown_duration_days"], 1),
        "calmar": round(m["calmar"], 4),
        "sqn": round(m["sqn"], 3),
        "kelly": round(m["kelly_fraction"], 3),
        "long_pnl": round(m["long_pnl"], 4),
        "short_pnl": round(m["short_pnl"], 4),
        "long_wr_pct": round(100 * m["long_win_rate"], 2),
        "short_wr_pct": round(100 * m["short_win_rate"], 2),
        "exits_tp": m["n_exits_tp"],
        "exits_sl": m["n_exits_sl"],
        "exits_other": m["n_exits_other"],
        "avg_hold_bars": round(m["avg_hold_bars"], 2),
        "exposure_pct": round(100 * m["exposure"], 2),
        "turnover": round(m["turnover"], 2),
        "fees": round(m["total_fees"], 4),
        "slippage": round(m["total_slippage"], 4),
        "funding": round(m["total_funding"], 4),
        "entry_bar_exit_rate_pct": round(100 * m["entry_bar_exit_rate"], 2),
        "skips": m["n_skips"],
        "liquidations": m["n_liquidations"],
        "liquidation_status": m["liquidation_status"],
        "buy_hold_return_pct": round(100 * m["buy_hold_return"], 2),
    }


data = {
    "btc": metric_block(btc_m),
    "eth": metric_block(eth_m),
    "trades": [slim(t) for t in btc_t] + [slim(t) for t in eth_t],
}
payload = json.dumps(data, separators=(",", ":"))

tsx = r"""import {
  Callout,
  Divider,
  Grid,
  H1,
  H2,
  H3,
  Pill,
  Row,
  Select,
  Spacer,
  Stack,
  Stat,
  Table,
  Text,
  useCanvasState,
  useHostTheme,
} from "cursor/canvas";

const DATA = __DATA__ as {
  btc: Record<string, any>;
  eth: Record<string, any>;
  trades: Array<{
    id: number;
    sym: string;
    side: string;
    entry: string;
    exit: string;
    ep: number;
    xp: number;
    pnl: number;
    fees: number;
    reason: string;
    hold: number;
    mae: number;
    mfe: number;
  }>;
};

type Sym = "ALL" | "BTCUSDT" | "ETHUSDT";
type Side = "ALL" | "long" | "short";

export default function PressureZone1dReport() {
  const theme = useHostTheme();
  const [sym, setSym] = useCanvasState<Sym>("sym", "BTCUSDT");
  const [side, setSide] = useCanvasState<Side>("side", "ALL");

  const metricSym = sym === "ALL" ? "BTCUSDT" : sym;
  const m = metricSym === "ETHUSDT" ? DATA.eth : DATA.btc;
  const trades = DATA.trades.filter((t) => {
    if (sym !== "ALL" && t.sym !== sym) return false;
    if (side !== "ALL" && t.side !== side) return false;
    return true;
  });

  const metricRows = [
    ["Period (days)", m.span_days],
    ["Longs / Shorts", `${m.n_longs} / ${m.n_shorts}`],
    ["Ending equity", m.ending_equity],
    ["Return on invested %", m.return_on_invested_pct],
    ["Wallet return %", m.wallet_return_pct],
    ["Buy & hold %", m.buy_hold_return_pct],
    ["Win rate Wilson 95% CI", `${m.win_rate_ci[0]}% – ${m.win_rate_ci[1]}%`],
    ["Avg win / avg loss", `${m.avg_win} / ${m.avg_loss}`],
    ["Best / worst trade", `${m.best_trade} / ${m.worst_trade}`],
    ["Long PnL / WR", `${m.long_pnl} / ${m.long_wr_pct}%`],
    ["Short PnL / WR", `${m.short_pnl} / ${m.short_wr_pct}%`],
    ["Exits TP / SL / other", `${m.exits_tp} / ${m.exits_sl} / ${m.exits_other}`],
    ["Avg hold bars", m.avg_hold_bars],
    ["Sortino annualised", m.sortino_ann],
    ["Calmar", m.calmar],
    ["Kelly fraction", m.kelly],
    ["Max DD duration (days)", m.max_dd_days],
    ["Turnover", m.turnover],
    ["Fees / slip / funding", `${m.fees} / ${m.slippage} / ${m.funding}`],
    ["Entry-bar exit rate", `${m.entry_bar_exit_rate_pct}%`],
    ["Skips", m.skips],
    ["Liquidations / status", `${m.liquidations} / ${m.liquidation_status}`],
  ].map(([k, v]) => [String(k), String(v)]);

  const tradeRows = trades.map((t) => [
    t.sym,
    t.side,
    t.entry,
    t.exit,
    t.ep,
    t.xp,
    t.pnl,
    t.fees,
    t.reason,
    t.hold,
    t.mae,
    t.mfe,
  ]);
  const tradeTone = trades.map((t) =>
    t.pnl >= 0 ? ("success" as const) : ("danger" as const)
  );

  return (
    <Stack gap={20} style={{ padding: 20, maxWidth: 1400 }}>
      <Stack gap={6}>
        <H1>Pressure zone — daily (1d) full report</H1>
        <Text tone="secondary">
          Strategy tsm_pressure_zone · Research proxy Binance Open-High-Low-Close-Volume with Bybit-style costs ·
          2020-01-01 → 2026-04-19 · Readiness LIVE_STOP / RESEARCH_ONLY · Conformance stamp NOT GREEN
        </Text>
        <Row gap={8}>
          <Pill tone="warning">Full-history exploratory (not stitched outer Out-Of-Sample)</Pill>
          <Pill>Funding = 0 in sim</Pill>
          <Pill tone="neutral">Liquidation status UNKNOWN</Pill>
        </Row>
      </Stack>

      <Callout tone="warning" title="Principal blocker">
        Profit Factor above 1 on daily bars is a hypothesis flag only. Sample is thin (BTC 184 / ETH 166 trades),
        engine stamp is NOT GREEN, and no frozen nested walk-forward has been run.
      </Callout>

      <H2>Headline metrics</H2>
      <Row gap={12} align="center">
        <Text weight="semibold">Metrics symbol</Text>
        <Select
          value={metricSym}
          onChange={(v) => setSym(v as Sym)}
          options={[
            { value: "BTCUSDT", label: "BTCUSDT" },
            { value: "ETHUSDT", label: "ETHUSDT" },
          ]}
        />
      </Row>
      <Grid columns={4} gap={12}>
        <Stat value={String(m.profit_factor)} label="Profit Factor" />
        <Stat value={`${m.win_rate_pct}%`} label="Win Rate" tone="info" />
        <Stat
          value={m.net_pnl.toFixed(2)}
          label="Net PnL (USDT)"
          tone={m.net_pnl >= 0 ? "success" : "danger"}
        />
        <Stat value={String(m.sharpe_ann)} label="Sharpe annualised (daily Mark-To-Market)" />
        <Stat value={String(m.hac_sharpe_ann)} label="HAC Sharpe annualised" />
        <Stat value={`${m.max_dd_pct}%`} label="Max drawdown (Mark-To-Market)" />
        <Stat value={String(m.n_trades)} label="Trades" />
        <Stat value={String(m.trades_per_month)} label="Trades / month" />
        <Stat value={String(m.expectancy)} label="Expectancy (USDT/trade)" />
        <Stat value={String(m.payoff_ratio)} label="Payoff ratio" />
        <Stat value={String(m.sqn)} label="System Quality Number (SQN)" />
        <Stat value={`${m.exposure_pct}%`} label="Exposure" />
      </Grid>

      <H3>Full metric block (selected symbol)</H3>
      <Table headers={["Metric", "Value"]} rows={metricRows} />

      <Divider />

      <H2>All trades</H2>
      <Text tone="secondary">
        CSV: artifacts/reports/tsm_pressure_zone/1d_full/SYMBOL/trades_all.csv · Finplot:
        python strategies/tsm_pressure_zone/run_1d_report_and_plot.py --symbol BTCUSDT --plot
      </Text>
      <Row gap={12} align="center">
        <Select
          value={sym}
          onChange={(v) => setSym(v as Sym)}
          options={[
            { value: "ALL", label: "All symbols" },
            { value: "BTCUSDT", label: "BTCUSDT" },
            { value: "ETHUSDT", label: "ETHUSDT" },
          ]}
        />
        <Select
          value={side}
          onChange={(v) => setSide(v as Side)}
          options={[
            { value: "ALL", label: "All sides" },
            { value: "long", label: "Long" },
            { value: "short", label: "Short" },
          ]}
        />
        <Text tone="secondary">Showing {trades.length} trades</Text>
      </Row>
      <Table
        stickyHeader
        striped
        headers={[
          "Symbol",
          "Side",
          "Entry",
          "Exit",
          "Entry px",
          "Exit px",
          "Realized PnL",
          "Fees",
          "Exit reason",
          "Hold bars",
          "MAE",
          "MFE",
        ]}
        rows={tradeRows}
        rowTone={tradeTone}
        columnAlign={[
          "left",
          "left",
          "left",
          "left",
          "right",
          "right",
          "right",
          "right",
          "left",
          "right",
          "right",
          "right",
        ]}
      />
      <Spacer size={12} />
      <Text tone="secondary" size="small">
        Theme {theme.kind} · MAE/MFE are path excursion fields from tradesim
      </Text>
    </Stack>
  );
}
"""

CANVAS.parent.mkdir(parents=True, exist_ok=True)
CANVAS.write_text(tsx.replace("__DATA__", payload), encoding="utf-8")
print("Wrote", CANVAS, "bytes", CANVAS.stat().st_size)
print("trades", len(data["trades"]))
