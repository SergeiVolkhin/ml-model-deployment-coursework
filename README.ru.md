# Развертывание ML моделей

[English](README.md) | [Русский](README.ru.md)

Решённые домашние задания магистерского курса «Развертывание ML моделей» (МФТИ,
2025-2026). Девять работ - от простого REST API до полной наблюдаемости - и итоговый
MLOps-проект. Каждое задание решает прикладную задачу развертывания и лежит в отдельной
папке с ноутбуком или проектом и кратким README. Программа курса - в файле
[силлабус](%282026%29%20Развертывание%20ML%20моделей_силлабус.pdf).

## Задания

| № | Тема | Папка | Что внутри | Ключевые технологии |
|---|------|-------|------------|---------------------|
| 1 | Основы REST API | [`hw1-api`](hw1-api/) | HTTP-сервер от `http.server` до FastAPI и клиент к нему | FastAPI, Pydantic, requests |
| 2 | Монолит против микросервисов | [`hw2-microservices`](hw2-microservices/) | Разбор архитектур через diagrams-as-code | diagrams, pandas, scikit-learn |
| 3 | Инфраструктура как код | [`hw3-iac`](hw3-iac/) | Починка и валидация сломанной конфигурации OpenTofu | OpenTofu/Terraform, Ansible |
| 4 | Лучшие практики Docker | [`hw4-docker`](hw4-docker/) | Сети, тома, лимиты ресурсов (ответ в PDF) | Docker, Docker Compose |
| 5 | Воспроизводимый ML-пайплайн | [`hw5-mlops`](hw5-mlops/) | Классификация вин с версионированием данных и фичестором | DVC, MLflow, Feast, scikit-learn |
| 6 | Асинхронный инференс и очереди | [`hw6-async-queue`](hw6-async-queue/) | Сервис эмбеддингов на Redis Streams с батчингом | FastAPI, Redis Streams, FastStream, torch |
| 7 | CI/CD и безопасный выкат | [`hw7-cicd`](hw7-cicd/) | Классификатор ирисов с canary, blue-green и A/B | GitHub Actions, GitLab CI, nginx |
| 8 | Мониторинг и наблюдаемость | [`hw8-monitoring`](hw8-monitoring/) | SLO, метрики, алерты, дрифт данных и проверки качества | Prometheus, Grafana, Evidently, DQOps, MLflow |
| 9 | Проектирование системы целиком | [`hw9-system-design`](hw9-system-design/) | Сравнение архитектур и DAG переобучения в Airflow | Airflow, MLflow, scikit-learn, Terraform |
| - | Итоговый проект: сквозная MLOps-платформа | [`final-mlops`](final-mlops/) | Полный цикл: данные, обучение, сервинг, мониторинг, переобучение | Airflow, MLflow, Feast, Evidently, SigLIP 2 |

## Стек

Python · FastAPI · Docker · Docker Compose · DVC · MLflow · Feast · Apache Airflow ·
Redis · FastStream · Prometheus · Grafana · Evidently · Terraform · GitHub Actions ·
scikit-learn · pytest

## Как запустить

```bash
git clone https://github.com/SergeiVolkhin/ml-model-deployment-coursework.git
cd ml-model-deployment-coursework
```

Каждое задание самодостаточно. Ноутбучные модули (HW1-HW3) ставят зависимости в первых
ячейках. Проектные модули (HW5-HW9 и итоговый) содержат свои `requirements.txt` или
`docker-compose.yml`:

```bash
cd hw5-mlops/ML-HW-hw5            # пример
python -m venv .venv
.venv\Scripts\activate           # Windows
source .venv/bin/activate         # Linux / macOS
pip install -r requirements.txt
```

Сервисные модули поднимаются командой `docker compose up`.

## Структура репозитория

```
.
├── hw1-api/                FastAPI сервер + клиент (http.server к FastAPI)
├── hw2-microservices/      монолит против микросервисов, diagrams-as-code
├── hw3-iac/                OpenTofu / Terraform, Ansible
├── hw4-docker/             сети, тома, лимиты ресурсов Docker (ответ в PDF)
├── hw5-mlops/              пайплайн DVC + MLflow + Feast
├── hw6-async-queue/        асинхронный инференс на Redis Streams + FastStream
├── hw7-cicd/               GitHub Actions + GitLab CI, canary / blue-green
├── hw8-monitoring/         Prometheus + Grafana + Evidently + DQOps
├── hw9-system-design/      Airflow DAG переобучения + Terraform
├── final-mlops/            итоговый проект: сквозная MLOps-платформа (uneemi)
└── (2026) Развертывание ML моделей_силлабус.pdf
```

## Автор

Вольхин Сергей Александрович

## Лицензия

MIT - см. [`LICENSE`](LICENSE).
