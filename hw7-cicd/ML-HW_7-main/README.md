# ML-HW_7. CI/CD пайплайн для ml-сервиса

Домашнее задание модуля 7 курса "Развертывание ML моделей" (МФТИ).
FastAPI-сервис с RandomForest на датасете iris, два docker-образа версий
v1.0.0 и v1.1.0, canary-деплой через nginx `split_clients`, пайплайны
GitLab CI и GitHub Actions.

## Структура

```
.github/workflows/         # GitHub Actions: ci.yml, deploy.yml
.gitlab-ci.yml             # GitLab CI: lint, test, train, build, reproducibility
app/                       # FastAPI service + RandomForest training
docker/                    # Dockerfile + compose стеки blue/green/canary
docker/nginx/              # nginx-шаблоны для blue-green и canary
doc/architecture/decisions # ADR (Michael Nygard format)
scripts/                   # deploy_canary.sh, rollback_canary.sh, smoke_test.sh
tests/                     # pytest для /health и /predict
HW7_CICD_Volkhin_Sergei.ipynb  # итоговый ноутбук со ссылками
```

## Локальный запуск

```bash
python -m venv .venv
source .venv/bin/activate          # на Windows: .venv\Scripts\activate
pip install -r requirements-dev.txt

# обучение модели и сохранение в app/models/model.pkl
python -m app.ml_pipeline --output-path app/models/model.pkl --random-state 42

# запуск API на http://localhost:8000
uvicorn app.main:app --host 0.0.0.0 --port 8000

# в другом терминале
curl http://localhost:8000/health
curl -X POST http://localhost:8000/predict \
  -H "Content-Type: application/json" \
  -d '{"x":[5.1,3.5,1.4,0.2]}'

# тесты и линт
pytest tests/ -v
ruff check app/ tests/
```

## Запуск в Docker

### Сборка образов v1.0.0 и v1.1.0

```bash
docker build -f docker/Dockerfile -t ml-service:v1.0.0 --build-arg MODEL_VERSION=v1.0.0 .
docker build -f docker/Dockerfile -t ml-service:v1.1.0 --build-arg MODEL_VERSION=v1.1.0 .
```

### Blue-Green

```bash
docker compose -f docker/docker-compose.blue.yml up -d
curl http://localhost:8001/health    # app-blue (v1.0.0)

docker compose -f docker/docker-compose.green.yml up -d
curl http://localhost:8002/health    # app-green (v1.1.0)

# переключение active upstream
bash scripts/switch_bluegreen.sh green
docker compose -f docker/docker-compose.blue.yml down
docker compose -f docker/docker-compose.green.yml down
```

### Canary 10/90

```bash
CANARY_WEIGHT=10 docker compose -f docker/docker-compose.canary.yml up -d

# /health доступен на http://localhost:8080
curl http://localhost:8080/health

# smoke-test 100 запросов с подсчётом долей по X-Service-Version
bash scripts/smoke_test.sh http://localhost:8080 100
# ожидаемый вывод:
#   [smoke] stable v1.0.0: 90
#   [smoke] canary v1.1.0: 10

# поэтапный rollout 10 -> 25 -> 50 -> 100
bash scripts/deploy_canary.sh

# откат на 100% stable
bash scripts/rollback_canary.sh
```

Для изменения веса канарейки на ходу:

```bash
docker exec -e CANARY_WEIGHT=25 ml-nginx sh -c \
  "DOLLAR='\$' envsubst '\$DOLLAR \$CANARY_WEIGHT' \
   < /templates/nginx.canary.conf.template > /etc/nginx/nginx.conf"
docker exec ml-nginx nginx -s reload
```

## Стратегия деплоя

Выбран Canary по причинам ограниченного blast radius (10% трафика вместо 100%
у Blue-Green) и возможности собирать live-метрики качества модели до полного
раскатывания. Полное обоснование с таблицей сравнения четырёх стратегий и
измеренное время отката - в [ADR-0002](doc/architecture/decisions/0002-use-canary-deployment.md).

## CI/CD

### GitLab CI

Пайплайн `.gitlab-ci.yml` со стадиями `lint -> test -> train -> build ->
reproducibility`. Шаг `reproducibility` сохраняет `pipeline_metadata.json`:
точные версии пакетов, git SHA, sha256 датасета и модели, random_state и
гиперпараметры. Артефакт хранится 1 месяц.

Ссылка на успешный пайплайн: https://gitlab.com/twinslolipop/ml-hw_7/-/pipelines/2516826220

### GitHub Actions

- `.github/workflows/ci.yml` - lint, test, train (с reproducibility),
  build-image push в GHCR при пуше в main.
- `.github/workflows/deploy.yml` - build-and-push с тегами sha + MODEL_VERSION,
  deploy с health-check (5 retry, 10с между попытками), auto-rollback при
  failure (`continue-on-error: true` + `if: steps.health.outcome == 'failure'`).

Ссылки на успешные runs:

- CI (lint, test, train, build): https://github.com/SergeiVolkhin/ML-HW_7/actions/runs/25689123899
- Deploy (build, push в GHCR, health-check): https://github.com/SergeiVolkhin/ML-HW_7/actions/runs/25689123863

### Секреты, которые нужно добавить

В Settings -> Secrets and variables -> Actions:

- `CLOUD_TOKEN` (secret) - токен cloud-провайдера для прод-деплоя
- `MODEL_VERSION` (variable) - переопределение версии модели при деплое

`GITHUB_TOKEN` поставляется автоматически.

## Откат

```bash
bash scripts/rollback_canary.sh
```

Скрипт подменяет nginx.conf на статический rollback-конфиг (100% на app-stable)
и вызывает `nginx -s reload`. Локальный замер на Windows 11 + Docker Desktop:
**439 мс** от запуска команды до завершения reload, после отката 100 из 100
запросов попадают на v1.0.0 (проверено `smoke_test.sh`).

## A/B тестирование

После полного раскатывания canary запускается A/B-эксперимент 50/50 с
рандомизацией по sha256(user_id). Sample size 1501 на группу (alpha=0.05,
power=80%, baseline 0.95, MDE 0.02). Полный план в
[ADR-0003](doc/architecture/decisions/0003-ab-testing-plan.md).
