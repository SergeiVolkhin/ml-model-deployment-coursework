# ML-инженерия: курсовые работы - МФТИ, Прикладная математика и информатика (2025-2026)

[English](README.md) | [Русский](README.ru.md)

![Python](https://img.shields.io/badge/Python-3.11-3776AB?logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-009688?logo=fastapi&logoColor=white)
![Docker](https://img.shields.io/badge/Docker-2496ED?logo=docker&logoColor=white)
![MLflow](https://img.shields.io/badge/MLflow-0194E2?logo=mlflow&logoColor=white)
![DVC](https://img.shields.io/badge/DVC-13ADC7?logo=dvc&logoColor=white)
![Airflow](https://img.shields.io/badge/Apache%20Airflow-017CEE?logo=apacheairflow&logoColor=white)
![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)

Репозиторий собирает мои выполненные работы по курсу «Развертывание ML моделей» (МФТИ,
магистратура, 2025-2026). Девять домашних заданий и итоговый проект проводят модель от
простого REST API через контейнеризацию, инфраструктуру как код, MLOps-инструменты,
асинхронный сервинг, CI/CD и мониторинг до полноценной production-платформы MLOps.
Каждая папка самодостаточна: свой ноутбук или проект и короткий README.

## Обзор заданий

| # | Тема | Стек | Статус |
|---|------|------|--------|
| HW1 | Основы REST API | FastAPI, Pydantic, requests, http.server | Готово |
| HW2 | Монолит против микросервисов | diagrams, pandas, scikit-learn | Готово |
| HW3 | Инфраструктура как код | OpenTofu/Terraform, Ansible | Готово |
| HW4 | Лучшие практики Docker | Docker, Docker Compose | Готово |
| HW5 | Воспроизводимый ML-пайплайн | DVC, MLflow, Feast, scikit-learn, PostgreSQL | Готово |
| HW6 | Асинхронный инференс + очереди | FastAPI, Redis Streams, FastStream, transformers, torch | Готово |
| HW7 | CI/CD + canary/blue-green | GitHub Actions, GitLab CI, nginx, FastAPI | Готово |
| HW8 | Мониторинг и наблюдаемость | Prometheus, Grafana, Evidently, DQOps, MLflow | Готово |
| HW9 | Проектирование системы целиком | Airflow, MLflow, scikit-learn, Terraform | Готово |
| Final | Сквозная MLOps-платформа | Airflow, MLflow, Feast, Evidently, SigLIP 2 (ONNX), Terraform | Готово |

## Установка

Каждое задание самодостаточно, большинство рассчитано на Python 3.11. Проектные папки
(с HW5 по HW9 и итоговый проект) содержат свои `requirements.txt` или `pyproject.toml`,
поэтому зависимости ставятся по папкам:

```bash
cd hw5-mlops/ML-HW-hw5          # пример
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

Ноутбучные задания (с HW1 по HW3) ставят свои немногочисленные зависимости прямо в
первых ячейках. Проекты на Docker/Compose поднимаются командой `docker compose up`.

## Структура репозитория

```
.
├── hw1-api/                FastAPI сервер + клиент (http.server к FastAPI)
├── hw2-microservices/      монолит против микросервисов, diagrams-as-code
├── hw3-iac/                OpenTofu / Terraform, Ansible
├── hw4-docker/             сети, тома, лимиты ресурсов Docker (ответ в PDF)
├── hw5-mlops/              пайплайн DVC + MLflow + Feast
│   └── ML-HW-hw5/
├── hw6-async-queue/        асинхронный инференс на Redis Streams + FastStream
│   └── ML-HW_6-main/
├── hw7-cicd/               GitHub Actions + GitLab CI, canary / blue-green
│   └── ML-HW_7-main/
├── hw8-monitoring/         Prometheus + Grafana + Evidently + DQOps
│   └── ML-HW_8-main/
├── hw9-system-design/      Airflow DAG переобучения + Terraform
│   └── ML-HW_9-main/
├── final-mlops/            итоговый проект: сквозная MLOps-платформа (uneemi)
│   └── uneemi-mlops-main/
└── (2026) Развертывание ML моделей_силлабус.pdf
```

## Автор

Сергей Вольхин - [GitHub](https://github.com/SergeiVolkhin) | МФТИ, магистратура «Прикладная математика и информатика»
