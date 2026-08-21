#!/usr/bin/env bash
# Install / refresh tsm-chandelier live bots on this VPS (94.x).
set -euo pipefail

ROOT=/opt/tsm-chandelier
SYMBOLS=(BTCUSDT ETHUSDT SOLUSDT)
LIVE_CANDLES_SRC=/opt/botsgeneral/packages/live_candles

cd "$ROOT"
python3 -m venv venv
./venv/bin/pip install -U pip
./venv/bin/pip install -r requirements.txt
if [[ -d "$LIVE_CANDLES_SRC" ]]; then
  ./venv/bin/pip install -e "$LIVE_CANDLES_SRC"
else
  echo "ERROR: $LIVE_CANDLES_SRC missing" >&2
  exit 1
fi

./venv/bin/python scripts/make_api_keys_from_botsgeneral.py \
  --src /etc/botsgeneral/bybit_keys.txt \
  --dst "$ROOT/config/api_keys.json" \
  --only Xxobster6

mkdir -p "$ROOT/data/live"
install -m 0644 deploy/tsm-chandelier@.service /etc/systemd/system/tsm-chandelier@.service
systemctl daemon-reload

for s in "${SYMBOLS[@]}"; do
  systemctl enable "tsm-chandelier@${s}.service"
  systemctl restart "tsm-chandelier@${s}.service"
done

echo "Installed units:"
for s in "${SYMBOLS[@]}"; do
  systemctl is-enabled "tsm-chandelier@${s}.service" || true
  systemctl is-active "tsm-chandelier@${s}.service" || true
done
