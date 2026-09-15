SHELL := /bin/bash
COMPOSE := docker compose -f deploy/compose/docker-compose.yml
INCLUDE_MONITORING := -f deploy/compose/docker-compose.monitoring.yml
INCLUDE_LOGGING := -f deploy/compose/docker-compose.logging.yml

.PHONY: help up down ps build logs test seed load k8s-apply

help: ## Показать справку
	@grep -E '^[a-zA-Z_-]+:.*?## ' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

up: ## Поднять приложение
	$(COMPOSE) up -d --build

up-all: ## Поднять приложение + мониторинг + логи
	$(COMPOSE) $(INCLUDE_MONITORING) $(INCLUDE_LOGGING) up -d --build

down: ## Остановить всё
	$(COMPOSE) $(INCLUDE_MONITORING) $(INCLUDE_LOGGING) down

ps: ## Статус контейнеров
	$(COMPOSE) $(INCLUDE_MONITORING) $(INCLUDE_LOGGING) ps

build: ## Собрать образы
	$(COMPOSE) build

logs: ## Логи всех сервисов
	$(COMPOSE) logs -f

test: ## Запустить юнит-тесты
	cd app/products && pytest -v
	cd app/orders && pytest -v

seed: ## Добавить демо-товары
	bash scripts/seed.sh

load: ## Сгенерировать нагрузку (используй: make load COUNT=500)
	bash scripts/load.sh $(COUNT) $(SLEEP_MS)

smoke: ## Smoke-тест
	bash scripts/smoke-test.sh

k8s-apply: ## Применить k8s-манифесты (нужен kubectl + кластер)
	kubectl apply -f deploy/k8s/ --recursive

helm-template: ## Проверить Helm-чарт локально
	helm lint deploy/helm/shopflow
	helm template shopflow deploy/helm/shopflow > /tmp/shopflow-manifests.yaml