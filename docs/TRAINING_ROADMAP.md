# Учебный маршрут: от 0 до продакшена (Ubuntu 22.04 в VMware)

Этот документ — пошаговый план, как пройти весь DevOps-стек проекта ShopFlow **реально, руками**, с пониманием того, что ты делаешь. На каждом этапе — цель, команды, объяснение, проверка и частые ошибки.

**Формат занятий:** 30–60 минут теории + 1–3 часа практики на этап. Не перепрыгивай этапы: каждый следующий опирается на предыдущий.

---

## Этап 0. Среда: Ubuntu Server в VMware + SSH

**Цель:** получить Linux-машину, к которой ты можешь подключаться по SSH. Всю дальнейшую работу делаем в ней (это и есть работа DevOps — серверы, а не твоя Windows-машина).

### Шаги
1. Скачай Ubuntu Server 22.04 LTS ISO: https://ubuntu.com/download/server
2. В VMware Workstation: *File → New Virtual Machine → Typical → Installer disc image (ISO)*.
3. Минимум ресурсов: **2 CPU, 4 GB RAM, 30 GB disk** (для K8s+ELK нужно место).
4. При установке создай пользователя `danil` (или свой). Опция *OpenSSH server* — включить.
5. После установки посмотри IP: `ip a` (обычно `192.168.x.x`).
6. С Windows: `ssh danil@192.168.x.x` — войдёшь в консоль.

### Как это устроено
- SSH — это шифрованный безопасный канал. Всё администрирование удалённых серверов происходит через него.
- Виртуалка даёт тебе чистый Linux без риска сломать Windows.

### Проверка
```bash
whoami          # danil
lsb_release -a  # Ubuntu 22.04
```

### Частые ошибки
- VMware не даёт IP — проверь сетевой адаптер VM (`NAT` вместо `Bridged` обычно надёжнее).
- Windows не находит `ssh` — в Windows 10+ OpenSSH client уже встроен.

---

## Этап 1. Ядро: Docker (образы и контейнеры)

**Цель:** понять разницу *образ → контейнер*, научиться собирать и запускать.

### Теория (5 минут)
- **Образ** = шаблон (слой с приложением и зависимостями, только для чтения).
- **Контейнер** = запущенный процесс из образа, с изолированными PID/network/filesystem.
- **Dockerfile** = рецепт сборки образа. Каждая строка — слой (слои кэшируются).

### Практика
```bash
sudo apt update && sudo apt install -y docker.io docker-compose-v2
sudo usermod -aG docker $USER   # чтобы не писать sudo
newgrp docker

# базовые команды — выучи их наизусть:
docker ps                       # запущенные контейнеры
docker ps -a                    # все контейнеры
docker images                   # образы
docker pull nginx
docker run -d -p 8080:80 --name web nginx
curl localhost:8080             # видим приветствие nginx
docker logs -f web
docker exec -it web bash        # зайти внутрь
docker stop web && docker rm web
```

### Разбор нашего Dockerfile (`app/products/Dockerfile`)
```dockerfile
FROM python:3.11-slim          # базовый образ
ENV PYTHONUNBUFFERED=1         # лог-идут сразу, без буфера
WORKDIR /app                   # рабочая директория
RUN addgroup --system app ...  # не root — безопасность!
COPY requirements.txt .        # сначала зависимости (кэш слоёв)
RUN pip install ...
COPY app ./app
USER app
HEALTHCHECK ...                # Docker умеет проверять живость процесса
CMD ["uvicorn", ...]
```

### Проверка
```bash
cd ~/shopflow/app/products
docker build -t shopflow-products .
docker run -d -p 8000:8000 --name products shopflow-products
curl localhost:8000/healthz    # {"status":"ok"}
docker inspect products | head -50   # смотри окружение, монтирования
```

### Задание для закрепления
Интервьюер почти наверняка спросит:
- "Чем отличается CMD от ENTRYPOINT?" — CMD можно перекрыть аргументами, ENTRYPOINT — фиксированная команда.
- "Зачем HEALTHCHECK?" — оркестратор (Docker/K8s) сам убивает сломанные контейнеры.

---

## Этап 2. Docker Compose: весь стек одной командой

**Цель:** поднять ShopFlow целиком — 3 сервиса + Postgres + Redis + RabbitMQ.

### Теория
Compose — декларативное описание многоконтейнерного приложения. `depends_on` задаёт порядок, `healthcheck` — готовность. Это «мост» к Kubernetes: там та же идея, только в YAML-манифестах.

### Практика
```bash
cd ~/shopflow
cp deploy/.env.example deploy/.env     # редактируй при желании
docker compose -f deploy/compose/docker-compose.yml up -d --build
docker compose -f deploy/compose/docker-compose.yml ps
docker compose -f deploy/compose/docker-compose.yml logs -f products

bash scripts/seed.sh                    # добавляем товары
bash scripts/smoke-test.sh              # E2E: заказ пройдёт через очередь
bash scripts/load.sh 500 20             # 500 заказов — нагрузка
```

### Разбор
- `postgres` поднимает **две** базы (см. `initdb/001_create_orders_db.sh`) — так два микросервиса не лезут в одни таблицы.
- `products` и `orders` — FastAPI, отдают метрики на `/metrics`.
- `worker` — потребитель из RabbitMQ. Создаёшь заказ → событие → worker «обрабатывает» → счётчик в Redis.

### Проверка
```bash
curl localhost:8001/api/v1/products           # список товаров
curl localhost:8002/api/v1/orders |head       # созданные заказы
# UI RabbitMQ: http://localhost:15672  (guest/guest) — посмотри очередь shopflow.orders
```

### Частые ошибки
- Контейнер `products` не стартует — Postgres ещё не готов: `depends_on` без `condition: service_healthy` не ждёт БД.
- Volume `postgres_data` заполнен старыми данными для чисто: `docker compose down -v`.

---

## Этап 3. Мониторинг и логи

**Цель:** увидеть происходящее в системе. Без этого DevOps не существует.

### Теория (3 термина за 5 минут)
- **Метрики** — числовые показатели (кол-во запросов, ошибки, latency). Собирает **Prometheus** (pull-модель: сам опрашивает `/metrics`).
- **Дашборды** — рисует **Grafana**, читая Prometheus.
- **Алерты** — правило в Prometheus → при срабатывании уходит в **Alertmanager**.
- **Логи** — другой тип данных (события, а не числа). Их собирает **ELK**.

### Практика
```bash
docker compose -f deploy/compose/docker-compose.yml \
             -f deploy/compose/docker-compose.monitoring.yml \
             -f deploy/compose/docker-compose.logging.yml up -d

# проверь, что всё поднялось
docker compose -f deploy/compose/docker-compose.monitoring.yml ps
```

Открой в браузере:
- **Prometheus**: `http://localhost:9090` → выполни запрос `up`. Видишь `1` для наших сервисов.
- **Grafana**: `http://localhost:3000` (admin / admin) → слева Dashboards → `ShopFlow Services`. Провижининг сам подхватил дашборд.
- **Kibana**: `http://localhost:5601` → Create index pattern `shopflow-*` → Discover. Логи приходят из всех контейнеров.

### Нагрузка для демо
```bash
bash scripts/load.sh 2000 5     # 2000 заказов — графики оживут
```
Посмотри в Grafana: HTTP requests/s, error rate, latency. Это красивая демонстрация на собеседовании.

### Как это связано с резюме
Фразе «снизил время реакции на инциденты на 40%» теперь соответствует то, что ты реально делал: алерт `HighErrorRate` (`monitoring/prometheus/rules/alerts.yml`) придет в Alertmanager при росте 5xx.

---

## Этап 4. CI/CD: GitHub Actions

**Цель:** автоматизировать тесты и публикацию образов при каждом push.

### Теория
- **CI** (Continuous Integration) — автотесты на каждое изменение → раньше ловим баги.
- **CD** (Continuous Delivery) — автоматический деплой (у нас — на VM по SSH).
- GitHub Actions = YAML-пайплайны, которые выполняются на раннерах GitHub.

### Практика
1. Пушь в `main`, открой вкладку **Actions** репозитория — увидишь 4 джобы (lint-and-test ×2, build-images ×3 — параллельно).
2. Джоба `lint-and-test`: на чистой машине ставит зависимости и гоняет `pytest`.
3. `build-images`: собирает Docker-образы и пушит в **GHCR** (GitHub Container Registry) как `ghcr.io/coput12/shopflow-*`.

### Что настроить руками (важно!)
В `deploy/helm/shopflow/values.yaml` и `deploy/k8s/*` уже стоит `coput12` — образы кластера будут тянуться из GHCR.

### Разбор правил в `ci.yml`
```yaml
on:
  push:            # на любой пуш
  pull_request:    # и пре-PR
```
```yaml
push: ${{ github.ref == 'refs/heads/main' || startsWith(github.ref, 'refs/tags/') }}
# образы публикуются ТОЛЬКО на main и тегах — на ветках не мусорим в registry
```
```yaml
cache-from: type=gha   # кэш слоёв между билдами — здорово ускоряет
```

### Задание
Ошибка в основной ветке должна ломать пайплайн — это нормально и хорошо. Потренируйся: сделай PR с тестом, который падает, посмотри на красный статус, почини.

---

## Этап 5. Kubernetes: манифесты и первые поды

**Цель:** понять core-концепции K8s. Используем **k3s** — лёгкий дистрибутив для одной машины (на собеседовании честно скажешь «работал в кластере на базе k3s — сертифицированном совместимом дистрибутиве»).

### Теория (главные объекты)
- **Pod** — минимальная единица: один или несколько контейнеров.
- **Deployment** — декларация «сколько подов и как обновлять».
- **Service** — стабильный адрес (= DNS) к подам, которые меняются.
- **Ingress** — внешний HTTP-вход по hostname/пути.
- **Namespace** — изоляция (у нас `shopflow`).
- **HPA** — Horizontal Pod Autoscaler: сам масштабирует поды по CPU/RAM.

### Практика
```bash
# k3s-провижининг уже написан на Ansible (см. этап 9), либо вручную:
curl -sfL https://get.k3s.io | sh -
sudo chmod 644 /etc/rancher/k3s/k3s.yaml
echo "export KUBECONFIG=/etc/rancher/k3s/k3s.yaml" >> ~/.bashrc && source ~/.bashrc

kubectl get nodes   # должен быть Ready
```

Применить наш набор манифестов:
```bash
cd ~/shopflow
# сначала создай секрет (пароли!) — см. deploy/k8s/02-secrets.example.yaml
kubectl apply -f deploy/k8s/ --recursive

kubectl get pods -n shopflow -w
kubectl get deploy -n shopflow
kubectl get hpa -n shopflow
```

### Изучи файлы (это твой ответ на «расскажи про твой K8s»)
- `deploy/k8s/products/deployment.yaml` — liveness/readiness пробы, requests/limits.
- `deploy/k8s/infra/postgres.yaml` — **StatefulSet** (нужен стабильный storage), почему не Deployment?
- `deploy/k8s/products/service-hpa.yaml` — автомасштабирование.

### Проверка kill -9 поды
```bash
kubectl delete pod -n shopflow --selector app=products   # Deployment поднимет новый
kubectl get pods -n shopflow    # новый под Ready — самовосстановление работает
```

---

## Этап 6. Helm: «docker compose» для K8s

**Цель:** понять, зачем шаблонизация. Один чарт = шаблон для любого сервиса.

### Теория
Helm-чарт — пакет манифестов с параметрами через `values.yaml`. У нас один чарт рендерит Deployment+Service+HPA для всех трёх сервисов (цикл по `values.services` в `templates/deployment.yaml`).

### Практика
```bash
cd ~/shopflow/deploy/helm/shopflow
helm lint .                                        # валидация
helm template shopflow . --namespace shopflow      # отрендерить без установки — ГЛАВНАЯ команда для отладки
helm upgrade --install shopflow . --namespace shopflow --create-namespace
helm list -n shopflow
helm upgrade shopflow . -n shopflow --set image.tag=v1.0.0   # обнови только тег
```

### Проверка поведения
Поменяй `replicas` в `values.yaml` → `helm upgrade shopflow . -n shopflow` → посмотри `kubectl get pods -n shopflow`.

### Вопрос на собеседовании
«Почему Helm, а не kustomize?» — Helm умеет чейнинг чартов (например, наш `shopflow` рядом с `kube-prometheus-stack`), версионирование релизов, откат `helm rollback`.

---

## Этап 7. Ingress и внешний доступ + мониторинг в кластере

**Цель:** отдавать сервисы наружу и наблюдать за кластером.

### Практика
```bash
# ingress-nginx уже ставился плейбуком k8s.yml; проверь:
kubectl get pods -n ingress-nginx

# примени роут: shopflow.local → /products*, /orders*
kubectl apply -f deploy/k8s/ingress.yaml
sudo bash -c 'echo "127.0.0.1 shopflow.local" >> /etc/hosts'
curl http://shopflow.local/products/api/v1/products     # (роут через rewrite-target)
```

### Мониторинг кластера одним чартом
```bash
helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
helm repo update
helm upgrade --install kube-prometheus prometheus-community/kube-prometheus-stack \
  --namespace monitoring --create-namespace --set grafana.adminPassword=admin
kubectl get pods -n monitoring
kubectl port-forward -n monitoring svc/kube-prometheus-grafana 3000:80
# Grafana на http://localhost:3000 — дашборды о самом кластере: CPU подов, контейнеры, падения
```
Почему через port-forward? Это стандартный способ добраться до внутреннего сервиса без публикации наружу.

---

## Этап 8. Ansible: автоматизация серверов

**Цель:** превратить ручные действия (этап 0–1) в повторяемый код. Ты уже это «написал» в `ansible/`.

### Теория
Ansible — агентлесс (работает по SSH), идемпотентный (сколько ни запускай — результат один). `become: true` = sudo.

### Практика
```bash
cd ~/shopflow/ansible
sudo apt install -y ansible-core
# местный pip для коллекции docker:
ansible-galaxy collection install community.docker

cp inventory/hosts.ini.example inventory/hosts.ini
nano inventory/hosts.ini    # заменяем CHANGE_ME на IP и пользователя

ansible-playbook playbooks/docker.yml -i inventory/hosts.ini
ansible-playbook playbooks/deploy-compose.yml -i inventory/hosts.ini
ansible-playbook playbooks/k8s.yml -i inventory/hosts.ini     # для кластера
```

### Разбор двух главных вещей
- `until: nodes.rc == 0 ...` — ждём готовности k3s, а не выходим с ошибкой.
- `when: false` в `deploy-compose.yml` — это «предохранитель»: реальный путь к `.env` на прод-машине ты задаёшь сам (лучше через `ansible-vault`).

### Задание
Добавь таск «Install jq» в `docker.yml`... он уже есть. Придумай свой: например, настроить `swapoff` (нужно для k8s) — это покажет владение Ansible, а не просто копирование.

---

## Этап 9. Terraform: инфраструктура как код

**Цель:** создавать серверы декларативно, а не консолью. Провайдер уже написан для **Yandex Cloud** (самый популярный у нас для практики).

### Теория
- **state** — Terraform помнит, что создал. Файл `.tfstate` — КРИТИЧЕН, потерял = «забыл» инфраструктуру.
- `plan` — показать, что будет сделано; `apply` — сделать; `destroy` — удалить.

### Практика
```bash
# у тебя на Windows
choco install terraform -y    # или winget install Hashicorp.Terraform

cd terraform
terraform init
# заполни terraform.tfvars (токены Yandex Cloud, SSH-ключ)
terraform plan -out plan.out
terraform apply plan.out      # на выходе получишь ssh-команду
ssh ubuntu@<public_ip>
```

### Ответы на вопросы собеседования
- «Как хранишь state?» — для личного проекта локально, для продакшена — remote (S3/YC Object Storage) + блокировки.
- «Зачем Terraform, если есть Ansible?» — Terraform = **облачные ресурсы** (VM, сети, диски), Ansible = **внутренности** серверов (пакеты, сервисы). Связка: Terraform создаёт VM → Ansible её готовит.

### Задание
Добавь в `terraform/vms.tf` вторую VM через `count`/`for_each` — это расчёт на многонодовый кластер и демонстрация уровня.

---

## Этап 10. Финальная проверка и «боевой» плечо

Перед собеседованием пройди весь стек с нуля на чистой VM за один вечер:

```bash
# чистая Ubuntu 22.04
git clone https://github.com/coput12/shopflow && cd shopflow
# 1. Compose-стек (этап 2)  →  curl healthz = ok
# 2. seed + smoke + load (этап 2-3)  →  Grafana дашборд живой
# 3. k3s (этап 5)  →  kubectl get pods -n shopflow = Running
# 4. Helm (этап 6)  →  helm list, kubectl get deploy
# 5. Мониторинг (этап 7)  →  Grafana показывает метрики кластера
```

### Чек-лист «что рассказать» (по одному предложению на блок)
| Блок | Фраза для резюме/интервью |
|---|---|
| Docker | «Собираю лёгкие non-root образы с HEALTHCHECK, слои кэшируются в CI» |
| Compose | «Поднимаю многосервисный стек с зависимостями по healthcheck'ам» |
| CI/CD | «Пайплайн из тестов и билда образов в GHCR, автодеплой по SSH» |
| K8s | «Манифесты + пробы + HPA + StatefulSet для БД, самовосстановление» |
| Helm | «Один чарт рендерит все сервисы через values.yaml» |
| Мониторинг | «Prometheus+Grafana+Alertmanager: дашборды, алерты на 5xx, latency» |
| Логи | «ELK: Filebeat→Logstash→Elasticsearch→Kibana, индексы по датам» |
| IaC | «Terraform создаёт VM в облаке, Ansible провижинит и деплоит» |

### Куда расти дальше (Senior-трек)
1. Безопасность: `sealed-secrets`/`SOPS`, `NetworkPolicies`, скан образов (Trivy).
2. Бэкапы: `pg_dump` в S3 + восстановление по алерту.
3. Нагрузка: k6/Locust + автоскейл по метрикам приложения (HPA по Prometheus-adapter).
4. Kafka вместо RabbitMQ (в проекте это один модуль — замени и прогони тест).
5. GitOps: **ArgoCD** — деплой из репозитория, а не по SSH. «Золотой стандарт» 2026.

---

## Шпаргалка по отладке

```bash
# Docker
docker ps -a; docker logs <container>; docker inspect <container>

# Compose
docker compose ps; docker compose logs -f <svc>

# K8s
kubectl get all -n shopflow
kubectl describe pod -n shopflow <pod>   # события: ImagePullBackOff, CrashLoop
kubectl logs -n shopflow <pod>
kubectl delete pod -n shopflow <pod>     # перезапустить проблемный под

# Helm
helm ls -n shopflow; helm history shopflow -n shopflow; helm rollback shopflow 1 -n shopflow

# Prometheus
# /targets — не все 200? <проблема со scrape>. /rules — алерты включились?
```

Если `ImagePullBackOff` — образ не существует в GHCR (стрейс может быть *pull access denied*). Исправление: запуши образ в GHCR или переключи `image.pullPolicy` локально.