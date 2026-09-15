#!/usr/bin/env bash
# Smoke-тест: проверяем health, создаём заказ, смотрим что worker его обработал.
set -euo pipefail

PRODUCTS_URL="${PRODUCTS_URL:-http://localhost:8001}"
ORDERS_URL="${ORDERS_URL:-http://localhost:8002}"

echo "== Products health =="
curl -sf "$PRODUCTS_URL/healthz" && echo

echo "== Orders health =="
curl -sf "$ORDERS_URL/healthz" && echo

echo "== Создаю заказ =="
curl -sf -X POST "$ORDERS_URL/api/v1/orders" \
  -H 'Content-Type: application/json' \
  -d '{"product_id":1,"quantity":2}' | python3 -m json.tool

echo "== Жду обработки worker =="
sleep 3

echo "== Statistik worker (Redis) =="
docker compose -f deploy/compose/docker-compose.yml exec redis redis-cli hgetall orders:status