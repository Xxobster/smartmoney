#!/bin/bash
set +e
echo "tsm-vpa requirements:"; head -n 20 /opt/tsm-vpa/requirements.txt
echo "live_candles:"; /opt/tsm-vpa/venv/bin/pip show live-candles 2>/dev/null | head -n 15
echo "botsgeneral packages:"; ls /opt/botsgeneral/packages 2>/dev/null
echo "api_keys accounts:"; python3 -c 'import json; print(sorted(json.load(open("/opt/tsm-vpa/config/api_keys.json"))))'
echo "Xxobster6 in bybit_keys:"; grep -n '\[Xxobster6\]\|^Xxobster6$' /etc/botsgeneral/bybit_keys.txt | head
echo "llm2 secrets env keys names only:"; if [ -f /root/.trading/secrets.env ]; then grep -E '^[A-Z0-9_]+=' /root/.trading/secrets.env | cut -d= -f1 | head -n 40; fi
