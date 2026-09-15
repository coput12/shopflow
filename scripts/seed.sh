#!/usr/bin/env bash
# Сидирование товаров (2-я база уже есть в compose). Запускать после старта compose.
set -euo pipefail

PRODUCTS_URL="${PRODUCTS_URL:-http://localhost:8001}"

curl -sf -X POST "$PRODUCTS_URL/api/v1/products" -H 'Content-Type: application/json' \
  -d '{"name":"Ноутбук DevBook 14","description":"14\", 16GB RAM","price":89999.0,"stock":50}' > /dev/null

curl -sf -X POST "$PRODUCTS_URL/api/v1/products" -H 'Content-Type: application/json' \
  -d '{"name":"Монитор 27\"","description":"2560x1440, IPS","price":29999.0,"stock":30}' > /dev/null

curl -sf -X POST "$PRODUCTS_URL/api/v1/products" -H 'Content-Type: application/json' \
  -d '{"name":"Механическая клавиатура","description":"TKL, brown switches","price":8990.0,"stock":100}' > /dev/null

echo "Товары добавлены:"
curl -sf "$PRODUCTS_URL/api/v1/products" | python3 -m json.tool