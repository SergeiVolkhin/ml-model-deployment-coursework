# HW8 - Monitoring and observability

A full observability stack for a recommender service: metrics, dashboards, alerts, drift detection, and data-quality checks.

## Stack

Prometheus, Grafana (Telegram alerting), Evidently (drift), DQOps + MySQL 8.4, MLflow, FastAPI ml_service, Docker Compose.

## Assignment

Stand up an end-to-end observability loop: SLO then metrics then Grafana dashboard then Telegram alert then data drift and model degradation via Evidently then a data-quality incident via DQOps on MySQL, plus an architecture rationale for real-time content swap (VPP, Kappa). I built the compose stack, a metrics tree across four branches (business, application, ML, infrastructure), and a load test that trips the latency alert.

## Files

| File | Description |
|------|-------------|
| `ML-HW_8-main/` | Main project: `ml_service/`, `prometheus/`, `grafana/`, `drift/`, `dqops/`, `mlflow/`, screenshots |
| `ML-HW_8-main/notebook/HW8_Monitoring_Volkhin_Sergei.ipynb` | Solution notebook |
| `Доп_семинар_Модуля_6_lambda_kappa_architecture.ipynb` | Seminar notebook (Lambda/Kappa architecture) |
| `Развертывание ML моделей_ Домашнее задание 8. Мониторинг.pdf` | Assignment specification |

Full project writeup: [`ML-HW_8-main/README.md`](ML-HW_8-main/README.md).

## Notes

Grafana's file-based provisioning could not type the Telegram chat id correctly, so I had to push the contact point through the REST API in a post-deploy script. Annoying, but it is the kind of thing you only find out by hitting it.
