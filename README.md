# ML Engineering Coursework - MIPT Applied Math & CS (2025-2026)

[English](README.md) | [Русский](README.ru.md)

![Python](https://img.shields.io/badge/Python-3.11-3776AB?logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-009688?logo=fastapi&logoColor=white)
![Docker](https://img.shields.io/badge/Docker-2496ED?logo=docker&logoColor=white)
![MLflow](https://img.shields.io/badge/MLflow-0194E2?logo=mlflow&logoColor=white)
![DVC](https://img.shields.io/badge/DVC-13ADC7?logo=dvc&logoColor=white)
![Airflow](https://img.shields.io/badge/Apache%20Airflow-017CEE?logo=apacheairflow&logoColor=white)
![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)

This repository collects my completed coursework for "Развертывание ML моделей"
(ML Model Deployment), a graduate course at MIPT (Moscow Institute of Physics and
Technology), 2025-2026. Nine homework assignments plus a capstone walk a model from a
bare REST API through containerization, infrastructure as code, MLOps tooling, async
serving, CI/CD, and monitoring, up to a full production-grade MLOps platform. Each
folder is self-contained with its own notebook or project and a short README.

## Assignments Overview

| # | Topic | Stack | Status |
|---|-------|-------|--------|
| HW1 | REST API fundamentals | FastAPI, Pydantic, requests, http.server | Done |
| HW2 | Monolith vs microservices | diagrams, pandas, scikit-learn | Done |
| HW3 | Infrastructure as Code | OpenTofu/Terraform, Ansible | Done |
| HW4 | Docker best practices | Docker, Docker Compose | Done |
| HW5 | Reproducible ML pipeline | DVC, MLflow, Feast, scikit-learn, PostgreSQL | Done |
| HW6 | Async inference + queues | FastAPI, Redis Streams, FastStream, transformers, torch | Done |
| HW7 | CI/CD + canary/blue-green | GitHub Actions, GitLab CI, nginx, FastAPI | Done |
| HW8 | Monitoring + observability | Prometheus, Grafana, Evidently, DQOps, MLflow | Done |
| HW9 | Whole-system design | Airflow, MLflow, scikit-learn, Terraform | Done |
| Final | End-to-end MLOps platform | Airflow, MLflow, Feast, Evidently, SigLIP 2 (ONNX), Terraform | Done |

## Setup

Each assignment is self-contained and most target Python 3.11. The project folders
(HW5 through HW9 and the final) ship their own `requirements.txt` or `pyproject.toml`,
so install dependencies per folder:

```bash
cd hw5-mlops/ML-HW-hw5          # example
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

The notebook-only assignments (HW1 through HW3) install their few dependencies inline
in the first cells. The Docker/Compose-based projects come up with `docker compose up`.

## Repository Structure

```
.
├── hw1-api/                FastAPI server + client (http.server to FastAPI)
├── hw2-microservices/      monolith vs microservices, diagrams-as-code
├── hw3-iac/                OpenTofu / Terraform, Ansible
├── hw4-docker/             Docker networks, volumes, resource limits (PDF answer)
├── hw5-mlops/              DVC + MLflow + Feast pipeline
│   └── ML-HW-hw5/
├── hw6-async-queue/        Redis Streams + FastStream async inference
│   └── ML-HW_6-main/
├── hw7-cicd/               GitHub Actions + GitLab CI, canary / blue-green
│   └── ML-HW_7-main/
├── hw8-monitoring/         Prometheus + Grafana + Evidently + DQOps
│   └── ML-HW_8-main/
├── hw9-system-design/      Airflow retraining DAG + Terraform
│   └── ML-HW_9-main/
├── final-mlops/            capstone: end-to-end MLOps platform (uneemi)
│   └── uneemi-mlops-main/
└── (2026) Развертывание ML моделей_силлабус.pdf
```

## Author

Sergei Volkhin - [GitHub](https://github.com/SergeiVolkhin) | MIPT MS Applied Math & CS
