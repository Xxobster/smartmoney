import json
from pathlib import Path

p = Path(r"D:\projects\smartmoney\artifacts\reports\tsm_chandelier\1h_monthly_trade_distribution.json")
d = json.loads(p.read_text(encoding="utf-8"))
print("package", d.get("package_hash_sha256") or "see freeze file")
print("btc_eth_avg", d["btc_eth_avg_trades_per_month"])
print("btc_eth_zero", d["btc_eth_zero_trade_months"])
print("btc_eth_max_zero_streak", d.get("btc_eth_max_consecutive_zero_months"))
for row in d["per_symbol"]:
    print("---", row["symbol"], row.get("status"))
    print(
        "trades",
        row.get("n_trades"),
        "pnl",
        row.get("net_pnl"),
        "pf",
        row.get("pooled_pf"),
        "avg/mo",
        row.get("avg_trades_per_month"),
        "median/mo",
        row.get("median_trades_per_month"),
        "zero_months",
        row.get("zero_trade_months"),
        "/",
        row.get("months_in_oos"),
        "max_zero_streak",
        row.get("max_consecutive_zero_months"),
    )
    # show months with n<=2 or n==0
    mt = row.get("monthly") or []
    thin = [m for m in mt if m["n_trades"] <= 2]
    print("thin_months(<=2)", thin[:20], "count", len(thin))
    if row["symbol"] == "SOLUSDT":
        print("SOL monthly:")
        for m in mt:
            print(f"  {m['month']}: n={m['n_trades']} pnl={m['net_pnl']:.3f}")
