#!/usr/bin/env bash
# Генерирует поток заказов — для красивого демо в Grafana.
# Запуск: bash scripts/load.sh 200 5  (200 заказов, пауза 5 мс)
set -euo pipefail

COUNT="${1:-200}"
SLEEP_MS="${2:-50}"
ORDERS_URL="${ORDERS_URL:-http://localhost:8002}"

echo "Генерирую $COUNT заказов..."

for i in $(seq 1 "$COUNT"); do
  product_id=$(( (i % 3) + 1 ))
  quantity=$(( (i % 5) + 1 ))
  curl -sf -o /dev/null -X POST "$ORDERS_URL/api/v1/orders" \
    -H 'Content-Type: application/json' \
    -d "{\"product_id\":$product_id,\"quantity\":$quantity}" || echo "fail order #$i"
  sleep "$(echo "scale=3; $SLEEP_MS/1000" | bc)"
done

echo "Готово. Redis счётчики:"
docker compose -f deploy/compose/docker-compose.yml exec redis redis-cli get stats:processed