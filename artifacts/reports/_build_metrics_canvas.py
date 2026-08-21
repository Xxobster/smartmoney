"""Build canvas of all TSM strategy metrics."""
from __future__ import annotations

import json
from pathlib import Path

SRC = Path(r"D:\projects\smartmoney\artifacts\reports\tsm_all_metrics.json")
CANVAS = Path(
    r"C:\Users\xxobs\.cursor\projects\d-projects-smartmoney\canvases\tsm-all-strategy-metrics.canvas.tsx"
)

rows = json.loads(SRC.read_text(encoding="utf-8"))

# Normalize display
for r in rows:
    if r.get("strategy") == "tsm_rsi_momentum_fib" and r.get("timeframe") in (None, "?", ""):
        r["timeframe"] = "15m"


def fmt_pct(x):
    if x is None:
        return "—"
    v = float(x)
    if v <= 1.5:
        v *= 100
    return f"{v:.1f}%"


def fmt_num(x, nd=2):
    if x is None:
        return "—"
    try:
        return f"{float(x):.{nd}f}"
    except (TypeError, ValueError):
        return str(x)


baselines = [r for r in rows if r["source"] == "full_history_baseline"]
oos = [r for r in rows if r["source"] == "nested_outer_oos_stitched"]

# Sort baselines by strategy, tf, symbol
order_tf = {"5m": 0, "15m": 1, "1h": 2, "1d": 3}

def sort_key(r):
    return (r["strategy"], order_tf.get(str(r["timeframe"]), 9), r["symbol"])

baselines.sort(key=sort_key)

base_table = [
    [
        r["strategy"].replace("tsm_", ""),
        r["symbol"],
        str(r["timeframe"]),
        int(r["n_trades"] or 0),
        fmt_num(r["trades_per_month"], 2),
        fmt_num(r["profit_factor"], 2),
        fmt_pct(r["win_rate"]),
        fmt_num(r["net_pnl"], 1),
        fmt_num(r["expectancy"], 3),
        fmt_num(r["sharpe_ann"], 2),
        fmt_num(r["hac_sharpe_ann"], 2),
        fmt_pct(r["max_drawdown"]),
    ]
    for r in baselines
]
base_tone = []
for r in baselines:
    pf = float(r["profit_factor"] or 0)
    if pf >= 1.0:
        base_tone.append("success")
    elif pf >= 0.9:
        base_tone.append("warning")
    else:
        base_tone.append("danger")

oos_table = [
    [
        r["strategy"].replace("tsm_", ""),
        r["symbol"],
        str(r["timeframe"]),
        int(r["n_trades"] or 0),
        fmt_num(r["trades_per_month"], 2),
        fmt_num(r["profit_factor"], 2),
        fmt_pct(r["win_rate"]),
        fmt_num(r["net_pnl"], 1),
        fmt_num(r["expectancy"], 3),
        fmt_num(r["sharpe_ann"], 2),
        fmt_num(r["hac_sharpe_ann"], 2),
        fmt_pct(r["max_drawdown"]),
        r.get("principal_blocker") or "—",
    ]
    for r in oos
]
oos_tone = ["danger" if float(r["profit_factor"] or 0) < 1 else "warning" for r in oos]

payload = json.dumps(
    {"base": base_table, "baseTone": base_tone, "oos": oos_table, "oosTone": oos_tone},
    separators=(",", ":"),
)

tsx = r"""import {
  Callout,
  Divider,
  H1,
  H2,
  Pill,
  Row,
  Stack,
  Table,
  Text,
} from "cursor/canvas";

const DATA = __DATA__ as {
  base: (string | number)[][];
  baseTone: Array<"success" | "warning" | "danger" | "info" | "neutral">;
  oos: (string | number)[][];
  oosTone: Array<"success" | "warning" | "danger" | "info" | "neutral">;
};

export default function TsmAllStrategyMetrics() {
  return (
    <Stack gap={20} style={{ padding: 20, maxWidth: 1500 }}>
      <Stack gap={6}>
        <H1>Secret Mindset — all tested strategy metrics</H1>
        <Text tone="secondary">
          Full-history exploratory baselines (~2020-01-01 → 2026-04-19) plus nested outer Out-Of-Sample where run.
          Evidence class RESEARCH_PROXY · readiness LIVE_STOP / RESEARCH_ONLY · engine stamp NOT GREEN
        </Text>
        <Row gap={8}>
          <Pill>Trades/month from tradesim headline (or OOS calendar)</Pill>
          <Pill>Win Rate reported, not a hard gate</Pill>
        </Row>
      </Stack>

      <Callout tone="warning" title="How to read this">
        Full-history Profit Factor is diagnostic only. Nested outer Out-Of-Sample is the selection headline for the two
        walk-forward candidates. Green row dots mark exploratory PF ≥ 1 (not a readiness pass).
      </Callout>

      <H2>Full-history baselines</H2>
      <Table
        stickyHeader
        striped
        headers={[
          "Strategy",
          "Symbol",
          "TF",
          "Trades",
          "Trades/mo",
          "PF",
          "WR",
          "Net PnL",
          "Expectancy",
          "Sharpe ann",
          "HAC Sharpe",
          "Max DD",
        ]}
        rows={DATA.base}
        rowTone={DATA.baseTone}
        columnAlign={[
          "left",
          "left",
          "left",
          "right",
          "right",
          "right",
          "right",
          "right",
          "right",
          "right",
          "right",
          "right",
        ]}
      />

      <Divider />

      <H2>Nested outer Out-Of-Sample (fixed H0)</H2>
      <Text tone="secondary">
        Pooled across BTCUSDT+ETHUSDT over five 180-day outer folds. Trades/month = pooled trades ÷ OOS calendar months.
      </Text>
      <Table
        stickyHeader
        striped
        headers={[
          "Strategy",
          "Symbols",
          "TF",
          "Trades",
          "Trades/mo",
          "PF",
          "WR",
          "Net PnL",
          "Expectancy",
          "Sharpe ann*",
          "HAC Sharpe*",
          "Max DD",
          "Blocker",
        ]}
        rows={DATA.oos}
        rowTone={DATA.oosTone}
        columnAlign={[
          "left",
          "left",
          "left",
          "right",
          "right",
          "right",
          "right",
          "right",
          "right",
          "right",
          "right",
          "right",
          "left",
        ]}
      />
      <Text tone="secondary" size="small">
        *Mean of per-symbol stitched daily Mark-To-Market Sharpes. CSV: artifacts/reports/tsm_all_metrics.csv
      </Text>
    </Stack>
  );
}
"""

CANVAS.write_text(tsx.replace("__DATA__", payload), encoding="utf-8")
print("Wrote", CANVAS, "baselines", len(base_table), "oos", len(oos_table))
