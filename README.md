# ML Model Deployment

[English](README.md) | [Русский](README.ru.md)

Completed coursework for the graduate course "Развертывание ML моделей" (ML Model
Deployment) at MIPT, 2025-2026. Nine homework assignments - from a bare REST API to full
observability - plus a capstone MLOps platform. Each assignment solves an applied
deployment task and lives in its own folder with a notebook or project and a short
README. The course program is in the [syllabus](%282026%29%20Развертывание%20ML%20моделей_силлабус.pdf).

## Assignments

| # | Topic | Folder | What's inside | Key tech |
|---|-------|--------|---------------|----------|
| 1 | REST API fundamentals | [`hw1-api`](hw1-api/) | HTTP server from `http.server` up to FastAPI, plus a client | FastAPI, Pydantic, requests |
| 2 | Monolith vs microservices | [`hw2-microservices`](hw2-microservices/) | Architecture study with diagrams-as-code | diagrams, pandas, scikit-learn |
| 3 | Infrastructure as Code | [`hw3-iac`](hw3-iac/) | Fixing and validating a broken OpenTofu config | OpenTofu/Terraform, Ansible |
| 4 | Docker best practices | [`hw4-docker`](hw4-docker/) | Networks, volumes, resource limits (PDF answer) | Docker, Docker Compose |
| 5 | Reproducible ML pipeline | [`hw5-mlops`](hw5-mlops/) | Wine classification with data versioning and a feature store | DVC, MLflow, Feast, scikit-learn |
| 6 | Async inference and queues | [`hw6-async-queue`](hw6-async-queue/) | Embedding service over Redis Streams with batching | FastAPI, Redis Streams, FastStream, torch |
| 7 | CI/CD and safe rollout | [`hw7-cicd`](hw7-cicd/) | Iris classifier with canary, blue-green and A/B rollout | GitHub Actions, GitLab CI, nginx |
| 8 | Monitoring and observability | [`hw8-monitoring`](hw8-monitoring/) | SLO, metrics, alerts, data drift and data-quality checks | Prometheus, Grafana, Evidently, DQOps, MLflow |
| 9 | Whole-system design | [`hw9-system-design`](hw9-system-design/) | Architecture comparison and a retraining Airflow DAG | Airflow, MLflow, scikit-learn, Terraform |
| - | Final: end-to-end MLOps platform | [`final-mlops`](final-mlops/) | Full lifecycle: data, training, serving, monitoring, retraining | Airflow, MLflow, Feast, Evidently, SigLIP 2 |

## Stack

Python · FastAPI · Docker · Docker Compose · DVC · MLflow · Feast · Apache Airflow ·
Redis · FastStream · Prometheus · Grafana · Evidently · Terraform · GitHub Actions ·
scikit-learn · pytest

## How to run

```bash
git clone https://github.com/SergeiVolkhin/ml-model-deployment-coursework.git
cd ml-model-deployment-coursework
```

Each assignment is self-contained. The notebook-only modules (HW1-HW3) install their few
dependencies in the first cells. The project modules (HW5-HW9 and the final) ship their
own `requirements.txt` or `docker-compose.yml`:

```bash
cd hw5-mlops/ML-HW-hw5            # example
python -m venv .venv
.venv\Scripts\activate           # Windows
source .venv/bin/activate         # Linux / macOS
pip install -r requirements.txt
```

Service modules come up with `docker compose up`.

## Repository structure

```
.
├── hw1-api/                FastAPI server + client (http.server to FastAPI)
├── hw2-microservices/      monolith vs microservices, diagrams-as-code
├── hw3-iac/                OpenTofu / Terraform, Ansible
├── hw4-docker/             Docker networks, volumes, resource limits (PDF answer)
├── hw5-mlops/              DVC + MLflow + Feast pipeline
├── hw6-async-queue/        Redis Streams + FastStream async inference
├── hw7-cicd/               GitHub Actions + GitLab CI, canary / blue-green
├── hw8-monitoring/         Prometheus + Grafana + Evidently + DQOps
├── hw9-system-design/      Airflow retraining DAG + Terraform
├── final-mlops/            capstone: end-to-end MLOps platform (uneemi)
└── (2026) Развертывание ML моделей_силлабус.pdf
```

## Author

Sergey Volkhin

## License

MIT - see [`LICENSE`](LICENSE).
