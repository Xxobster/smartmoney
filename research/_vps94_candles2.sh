python3 <<'PY'
import sqlite3, time
con=sqlite3.connect('/var/lib/botsgeneral/shared_candles.db')
cols=[c[1] for c in con.execute('pragma table_info(candles)')]
print('cols', cols)
# guess exchange column
excol='exchange' if 'exchange' in cols else ('source' if 'source' in cols else None)
print('excol', excol)
qbase="select {ex}, symbol, timeframe, count(*), max(ts_ms) from candles where symbol in ('BTCUSDT','ETHUSDT','SOLUSDT') and timeframe in ('1h','1m') group by 1,2,3 order by 2,3,1"
if excol:
    rows=con.execute(qbase.format(ex='exchange' if excol=='exchange' else 'source')).fetchall()
else:
    rows=con.execute("select symbol, timeframe, count(*), max(ts_ms) from candles where symbol in ('BTCUSDT','ETHUSDT','SOLUSDT') and timeframe in ('1h','1m') group by 1,2").fetchall()
now=time.time()*1000
for r in rows:
    mx=r[-1]
    age=(now-mx)/3.6e6 if mx else None
    print(r, f'age_h={age:.2f}' if age is not None else '')
print('discovered', con.execute('select * from discovered_pairs limit 20').fetchall())
PY
