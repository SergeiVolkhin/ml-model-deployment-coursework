# ADR 0002 - Стек наблюдаемости: Prometheus + Grafana + MLflow

Дата: 2026-05-16
Статус: принято

## Контекст

ML-сервису ДЗ-8 нужен мониторинг с поддержкой SLO (latency p95 < 1s, error rate < 1%, availability > 99%), плюс отдельный canal для ML-специфичных артефактов (эксперименты, модели). Среда - docker-compose на Windows + Docker Desktop, плюс перспектива продакшена в Kubernetes.

## Альтернативы

### A. ELK / OpenSearch (logs-first)

Лог-центричный подход: всё пишем в логи, кубики через elastic / opensearch. Плюсы: единый search-интерфейс. Минусы: дорого хранить, медленные numeric-агрегации, плохо для high-cardinality histogram'ов (квантили требуют sketch'ей).

### B. Datadog / NewRelic SaaS

Платные SaaS. Плюсы: zero-ops. Минусы: дорого при росте, vendor lock-in, не подходит для академической задачи.

### C. Prometheus + Grafana + MLflow

Open-source de-facto стандарт SRE-сообщества. Prometheus - pull-модель скрейпинга метрик с встроенной TSDB; Grafana - визуализация + алертинг (включая Telegram); MLflow - отдельный сервис для tracking, regstry и model lifecycle. Минусы: три сервиса вместо одного.

## Решение

Выбран вариант C. Конкретные версии (зафиксированы в `.env.example`):
- `prom/prometheus:v3.11.3`
- `grafana/grafana:13.0.1`
- `ghcr.io/mlflow/mlflow:v3.12.0`

ML-сервис экспортирует Prometheus-метрики через `prometheus_client`. Grafana провижионится конфигами в `grafana/provisioning/` (datasource + dashboard + alert rule + Telegram contact point). MLflow используется как side-channel: при старте ml_service логирует dummy baseline-модель, в проде эта точка станет integration-местом с retrain-pipeline.

Алертинг сделан с дублированием: PromQL правило в `prometheus/alerts.yml` плюс Grafana alert rule в `grafana/provisioning/alerting/alert-rules.yml`. Это позволяет:
- Демонстрировать рубрику Шага 2 (Prometheus как первичная сигнальная плоскость).
- Использовать Grafana Telegram contact point (Prometheus сам не отправляет в Telegram без Alertmanager).
- Иметь fallback, если один из стеков нездоров.

## Последствия

Положительные:
- Все три инструмента индустриальные, портируются в Kubernetes без переписывания (`kube-prometheus-stack` Helm chart, Grafana operator, MLflow на K8s native deployment).
- Метрики не привязаны к коду приложения - можно сменить FastAPI на любой другой framework без изменения дашборда.
- MLflow даёт явный artifact-store для воспроизводимости.

Отрицательные:
- Три сервиса в compose - 4-й контейнер MLflow увеличивает RAM-следокий до ~1.5 GB.
- Высокая cardinality лейблов (например, `endpoint=/predict/v123/...`) может взорвать TSDB - в README указано избегать unbounded label values.

Митигации:
- Buckets гистограммы зафиксированы под SLO (10 buckets, последний 5s).
- В compose - `--storage.tsdb.retention.time=7d` для Prometheus, избегаем разрастания данных.
- MLflow backend на sqlite-volume, на проде менять на Postgres + S3-совместимое хранилище артефактов.
