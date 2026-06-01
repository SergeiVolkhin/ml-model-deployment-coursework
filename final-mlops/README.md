# Final - End-to-end MLOps platform (capstone)

A production-grade MLOps system (uneemi) covering the full model lifecycle, from data cleaning and training to retiring an old model by switching traffic to a new one.

## Stack

Python 3.11, Apache Airflow 2.10.4, MLflow 2.22.1, Feast 0.40.1 (Redis online + parquet/MinIO offline), Evidently 0.4.40, SigLIP 2 (ONNX), FastAPI serving, Prometheus/Grafana, Terraform, Docker Compose, GitHub Actions.

## Assignment

The capstone builds a complete MLOps platform: feature, training, and monitoring pipelines as Airflow DAGs; champion/challenger promotion behind a quality gate; hot model swap in serving without a restart; drift-triggered continuous training (Evidently, PSI); and guardrail rollback on a latency or error-rate breach. SigLIP 2 runs as an ONNX feature encoder producing 768d board embeddings.

## Files

| File | Description |
|------|-------------|
| `uneemi-mlops-main/` | Full MLOps project: `dags/`, `serving/`, `feature_repo/`, `monitoring/`, `infra/`, `training/`, `docs/`, `tests/` |
| `Задание.pdf` | Final assignment specification |
| `компоненты из перечня.pdf` | Required components list (C1-C9, Kreuzberger et al.) |
| `MLOps Continuous delivery.pdf` | Reference material |

Full project writeup: [`uneemi-mlops-main/README.md`](uneemi-mlops-main/README.md). This project is also published at [github.com/SergeiVolkhin/uneemi-mlops](https://github.com/SergeiVolkhin/uneemi-mlops).

## Notes

The piece I am most happy with is the champion/challenger gate. A challenger only reaches Production if its holdout ROC-AUC clears the threshold and beats the current champion, so promotion is never just "newer wins". The old version moves to Archived automatically and serving picks up the new one hot.
