#!/bin/bash
set +e
systemctl restart botsgeneral-collector@94.156.189.76.service
sleep 2
echo "collector=$(systemctl is-active botsgeneral-collector@94.156.189.76.service)"
for s in BTCUSDT ETHUSDT SOLUSDT; do
  echo "===== $s ====="
  systemctl is-active "tsm-chandelier@${s}.service"
  journalctl -u "tsm-chandelier@${s}.service" -n 35 --no-pager
done
echo "===== accounts in keys ====="
python3 -c 'import json; print(sorted(json.load(open("/opt/tsm-chandelier/config/api_keys.json"))))'
echo "===== discovered demand ====="
python3 - <<'PY'
import sqlite3, time
con=sqlite3.connect('/var/lib/botsgeneral/shared_candles.db')
rows=con.execute("select exchange,symbol,timeframe,requested_by,updated_at_ms from discovered_pairs where requested_by like '%chand%' or (symbol in ('BTCUSDT','ETHUSDT','SOLUSDT') and timeframe='1h') order by 1,2").fetchall()
for r in rows:
    print(r)
PY
