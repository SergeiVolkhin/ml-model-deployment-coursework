# Готовность ML-системы к продакшену

## 1. Из чего состоит полноценная ML-система

| # | Компонент | Зачем |
|---|---|---|
| 1 | Data Pipeline (ETL) | Получение, очистка, валидация сырых данных. Schema/quality-чеки. |
| 2 | Feature Store | Версионирование фичей, единая логика train/serve, переиспользование между моделями. |
| 3 | Experiment Tracking | Параметры, метрики, артефакты каждого запуска. Для сравнения и отката. |
| 4 | Model Registry | Версии моделей, стейджи (staging/prod), метаданные lineage. |
| 5 | Training Orchestration | Регулярные ретрейны по расписанию или триггеру (Airflow, Argo, Kubeflow). |
| 6 | CI/CD для ML | Тесты на код, на данные, на модель; автодеплой после прохождения gates. |
| 7 | Inference Service | Низколатентный online (REST/gRPC) и/или batch. Канареечные деплои, shadow. |
| 8 | Online Feature Serving | Чтение фичей в момент инференса с low latency (Redis, online Postgres). |
| 9 | Model Monitoring | Latency, throughput, error rate. Quality of predictions vs ground truth. |
| 10 | Data/Concept Drift Detection | Автоматическое отслеживание сдвига распределений. Триггер на ретрейн. |
| 11 | A/B Testing / Shadow / Multi-armed bandit | Сравнение моделей в продакшен-трафике с контролем риска. |
| 12 | Lineage & Reproducibility | Связь "данные → код → модель → деплой" для аудита и отката. |
| 13 | Cost & Resource Monitoring | GPU usage, стоимость инференса на запрос, бюджеты на обучение. |

## 2. Что есть в этом проекте vs что требуется в проде

| Компонент | Реализовано | Промышленный gap |
|---|---|---|
| Data Pipeline | DVC stage `prepare` (split + сохранение) | Нет валидации схемы/качества, нет ingestion из реального источника |
| Feature Store | Feast + PostgreSQL (offline+online), `feast apply`, `feast materialize` | Нет push-источника событий, не подключено к training напрямую |
| Experiment Tracking | MLflow: params, metrics (4 шт), artifacts (model, confusion matrix, sklearn model) | Tracking сервер локальный (sqlite), не shared, без auth |
| Model Registry | `mlflow.sklearn.log_model` создает запись, но не используется stage-промоут | Нет staging/production переходов, нет approval workflow |
| Training Orchestration | DVC repro - воспроизводимый локально | Нет расписания, нет триггеров на новые данные, не запускается на cluster |
| CI/CD | - | Нет GitHub Actions, нет автотестов кода/данных/модели |
| Inference Service | - | Нет REST/gRPC сервиса, нет контейнеризации модели |
| Online Feature Serving | Feast online store работает (проверено) | Не подключен к inference-сервису (его нет) |
| Model Monitoring | - | Нет Prometheus/Grafana, нет логов предсказаний |
| Drift Detection | - | Нет evidently/whylabs/собственных метрик |
| A/B Testing | - | Нет shadow/canary, нет route-роутинга |
| Lineage | DVC + MLflow дают связку код+данные+модель | Нет end-to-end lineage до продовых запросов |
| Cost Monitoring | - | Не релевантно на этапе ноутбука |

## 3. Сценарий "только Colab + git"

Это типичная стартовая точка: ноутбук с обучением модели лежит в репозитории. По шкале готовности к продакшену - примерно **5-10%**.

Что есть: код модели и метрики в outputs ячеек.

Чего нет (в порядке убывания критичности):
- **Воспроизводимость**: версии библиотек плавают (`!pip install` без pin), данные в Drive у автора, рандом-сиды могут быть не зафиксированы. Условие "git clone + одна команда → те же метрики" не выполняется.
- **Версионирование данных**: CSV в репо или в личном Drive - нет хеша, нет remote storage, история изменений теряется.
- **Tracking**: метрики живут в outputs ячейки, при перезапуске затираются. Сравнить два эксперимента можно только глазами по вкладкам Colab.
- **Оркестрация**: ноутбук запускается вручную. Ретрейн = "найти автора, попросить запустить".
- **Inference**: нет. Модель в .pkl лежит у автора локально или в Drive.
- **CI/CD**: Colab не интегрирован с pipeline-ами.

## 4. Оценка текущего проекта

С учетом реализованных компонентов:

- ✅ Data versioning (DVC + remote)
- ✅ Reproducible pipeline (`dvc repro` дает те же метрики)
- ✅ Experiment tracking (MLflow с params/metrics/artifacts)
- ✅ Feature Store (Feast + Postgres, online retrieval работает)
- ⚠️ Model tracking есть, но не используется как Registry
- ❌ Нет inference, monitoring, CI/CD, drift detection, A/B

**Готовность к продакшену: ~35-40%.**

Это уровень "research-ready repo" / "MLOps level 0-1" по таксономии Google. Достаточно для:
- передачи модели другому инженеру с гарантией воспроизводимости;
- сравнения нескольких подходов через MLflow UI;
- использования фичей в нескольких пайплайнах через Feast.

Недостаточно для:
- production-инференса под трафиком;
- автоматического ретрейна по расписанию или дрейфу;
- безопасного выкатывания новой модели (нет A/B / shadow);
- наблюдаемости после деплоя.

## 5. Что добавить до production-grade (приоритеты)

1. **Containerize**: Dockerfile для сервиса инференса (FastAPI + загрузка модели из MLflow registry).
2. **CI/CD**: GitHub Actions - lint, тесты, `dvc repro`, gating на метрику (accuracy не упала).
3. **Model Registry promotion**: API/CLI-промоут после прохождения gates.
4. **Inference monitoring**: Prometheus exporter в сервисе, Grafana dashboard, alerts на p99 latency и error rate.
5. **Drift detection**: evidently на батчах входных данных, триггер ретрейна в Airflow/Argo.
6. **Канареечный деплой**: маршрутизация 5% трафика на новую версию через service mesh.
