#!/bin/sh
# Создаёт дополнительные БД (shopflow_orders) в одном Postgres-инстансе.
# Postgres запускает этот скрипт при первом старте (docker-entrypoint-initdb.d).
set -e

psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<-EOSQL
    CREATE DATABASE shopflow_orders;
EOSQL