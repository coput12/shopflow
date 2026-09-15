# ShopFlow — DevOps-проект для портфолио

Платформа микросервисного интернет-магазина: **3 сервиса на FastAPI**, событийный обмен через **RabbitMQ**, кэширование в **Redis**, хранение в **PostgreSQL**, упаковка в **Docker**, оркестрация в **Kubernetes** через **Helm**, инфраструктура как код на **Terraform + Ansible**, наблюдение через **Prometheus + Grafana + Alertmanager** и логи в **ELK**.

> Цель проекта: показать полный продакшен-цикл — от кода до мониторинга. Каждый каталог закрывает конкретный пункт моего резюме.

## Архитектура

```
                    ┌───────────────────────────────┐
                    │     CI/CD (GitHub Actions)     │
                    │  тесты → сборка → публикация   │
                    └──────────────┬────────────────┘
                                   │
  ┌───────────────┐    ┌───────────▼────────────┐    ┌───────────────┐
  │   products    │    │         orders          │    │    worker     │
  │  FastAPI CRUD │    │  FastAPI + RabbitMQ     │    │ consumer +    │
  │  Postgres+DB  │    │  публикует события      │    │ Prometheus    │
  │  Redis-кэш    │    │  order.created          │    │ метрики       │
  └───────┬───────┘    └───────┬────────┬────────┘    └───────┬───────┘
          │                    │        │                     │
      PostgreSQL           RabbitMQ    │                 Redis (статистика)
          │                    │        │                     │
      └────────────────────────┴────────┴─────────────────────┘
                                   │
                ┌──────────────────┼──────────────────┐
                ▼                  ▼                  ▼
        Prometheus/Alertmanager  Grafana            ELK
           (метрики)           (дашборды)         (логи)
```

### Стек и что он закрывает в резюме

| Компонент    | Каталог                               | Пункт резюме                       |
|--------------|---------------------------------------|-------------------------------------|
| 3 сервиса    | `app/`                                | Python, микросервисы               |
| Docker       | `app/*/Dockerfile`, `deploy/compose/` | Docker, Docker-compose              |
| Очереди      | RabbitMQ в compose и K8s              | Apache Kafka/RabbitMQ (аналог — easy swap на Kafka) |
| CI/CD        | `.github/workflows/`, `.gitlab-ci.yml`| GitLab CI / CI/CD                   |
| K8s          | `deploy/k8s/`, `deploy/helm/`         | Kubernetes, Helm                    |
| IaC          | `terraform/`, `ansible/`              | Terraform, Ansible                  |
| Мониторинг   | `monitoring/`, `deploy/helm`          | Prometheus, Grafana                 |
| Логи         | `deploy/compose/logging/`             | ELK                                 |
| Базы данных  | PostgreSQL (X2), MySQL (необяз.), Redis| PostgreSQL, MySQL, Redis           |

## Быстрый старт (локально / на VM)

### 1. Docker Compose (быстрый контур)

```bash
cp deploy/.env.example deploy/.env            # поправь значения
docker compose -f deploy/compose/docker-compose.yml up -d --build

bash scripts/seed.sh                          # добавить товары
bash scripts/smoke-test.sh                    # проверить E2E
bash scripts/load.sh 500 20                   # нагрузка: 500 заказов
```

Endpoints:
- Products API: `http://localhost:8001` (доки: `/api/v1/docs`)
- Orders API: `http://localhost:8002`
- RabbitMQ UI: `http://localhost:15672` (guest/guest)

### 2. Мониторинг + Логи

```bash
docker compose -f deploy/compose/docker-compose.yml \
             -f deploy/compose/docker-compose.monitoring.yml \
             -f deploy/compose/docker-compose.logging.yml up -d
```

- Prometheus: `http://localhost:9090`
- Alertmanager: `http://localhost:9093`
- Grafana: `http://localhost:3000` (admin/admin) — дашборд `ShopFlow Services` провижинится автоматически
- Kibana: `http://localhost:5601`

### 3. Kubernetes (k3s/kind) + Helm

```bash
# один узел:
ansible-playbook ansible/playbooks/k8s.yml -i ansible/inventory/hosts.ini

# или вручную: kind create cluster / k3d

# инфраструктура (postgres, redis, rabbitmq):
kubectl apply -f deploy/k8s/ --recursive

# приложение через Helm:
helm lint deploy/helm/shopflow
helm upgrade --install shopflow deploy/helm/shopflow -n shopflow

# мониторинг в кластер:
helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
helm upgrade --install kube-prometheus prometheus-community/kube-prometheus-stack -n monitoring --create-namespace
```

### 4. Инфраструктура как код

```bash
cd terraform
terraform init
terraform plan -out plan.tfout
terraform apply plan.tfout
# получишь публичный IP VM

cd ../ansible
cp inventory/hosts.ini.example inventory/hosts.ini   # впиши IP
ansible-galaxy install -r requirements.yml
ansible-playbook playbooks/docker.yml -i inventory/hosts.ini
ansible-playbook playbooks/deploy-compose.yml -i inventory/hosts.ini
```

## CI/CD

[`.github/workflows/ci.yml`](.github/workflows/ci.yml) — на каждый push:
1. юнит-тесты сервисов (`pytest`),
2. сборка образов в GHCR (кеш через buildx cache),
3. публикация на `main`/теги.

[`.github/workflows/cd.yml`](.github/workflows/cd.yml) — деплой на VM по SSH при пуше в `main`.

Аналог для GitLab — [`.gitlab-ci.yml`](.gitlab-ci.yml) (3 стадии: test → build → deploy).

## Известные проблемы и следующий шаг

- Пароли в примерах — демонстрационные. Перед реальным запуском: `sealed-secrets`/`external-secrets`/`SOPS` + remote state для Terraform.
- RabbitMQ легко заменить на Apache Kafka (в `app/orders` и `app/worker` только один модуль публикации/потребления) — оставлено как задача для роста.
- Для production-кластера: несколько нод k3s, `storageClass` для Postgres, бэкапы (pg_dump + S3), `NetworkPolicies`.
- Нагрузочные тесты: `locust`/`k6` для дальнейшего growth-демо в Grafana.

## Структура репозитория

```
├── app/
│   ├── products/   FastAPI + Postgres + Redis-кэш + тесты
│   ├── orders/     FastAPI + публикация событий в RabbitMQ
│   └── worker/     consumer + Prometheus-метрики
├── deploy/
│   ├── compose/    docker-compose (app, monitoring, logging)
│   ├── k8s/        манифесты (namespace, deployments, hpa, ingress, infra)
│   └── helm/       чарт shopflow
├── terraform/      создание VM (Yandex Cloud)
├── ansible/        provision Docker/k3s, деплой приложения
├── monitoring/     конфиги Prometheus, Alertmanager, Grafana
└── scripts/        seed, smoke, load
```