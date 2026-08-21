set +e
echo "HOST=$(hostname) IP=$(hostname -I | awk '{print $1}')"
echo "collector=$(systemctl is-active botsgeneral-collector@94.156.189.76.service)"
python3 <<'PY'
import sqlite3, time
db='/var/lib/botsgeneral/shared_candles.db'
con=sqlite3.connect(db)
tables=[r[0] for r in con.execute("select name from sqlite_master where type='table'")]
print('tables', tables[:15])
for t in tables:
    cols=[c[1] for c in con.execute(f'pragma table_info({t})')]
    if 'symbol' in cols and 'timeframe' in cols and 'ts_ms' in cols:
        print('ohlcv_table', t)
        for sym in ['BTCUSDT','ETHUSDT','SOLUSDT']:
            for src in ['binance','bybit']:
                row=con.execute(
                    f"select count(*), max(ts_ms) from {t} where symbol=? and timeframe='1h' and source=?",
                    (sym, src)
                ).fetchone()
                n, mx = row[0], row[1]
                if n:
                    age=(time.time()*1000-mx)/3.6e6
                    print(f'  {src} {sym}: n={n} age_h={age:.2f}')
        break
PY
echo "=== llm2 xxobster6 units ==="
systemctl list-units --all --no-pager | grep -Ei 'llm2|Xxobster6' | head -n 40
for u in llm2-structure-eth-k5-double3h-v1.service llm2-structure-eth.service llm2-structure-micro.service; do
  echo "-- $u --"
  systemctl is-enabled "$u" 2>/dev/null; systemctl is-active "$u" 2>/dev/null
  systemctl show "$u" -p ActiveState -p SubState -p FragmentPath --no-pager 2>/dev/null
done
echo "=== processes mentioning Xxobster6 or micro_runner ==="
ps -eo pid,cmd | grep -Ei 'Xxobster6|micro_runner|tsm_chandelier|tsm-chandelier' | grep -v grep | head -n 40
echo "=== keys have Xxobster6? ==="
python3 - <<'PY'
from pathlib import Path
for p in [Path('/opt/tsm-vpa/config/api_keys.json'), Path('/home/xgb/api_keys.json'), Path('/etc/botsgeneral/bybit_keys.txt')]:
    if not p.exists():
        continue
    txt=p.read_text(errors='ignore')
    print(p, 'Xxobster6' in txt or 'xxobster6' in txt.lower())
PY
