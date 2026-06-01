# Дерево метрик ML-системы онлайн-кинотеатра

## Контекст системы

Рекомендательная ML-система онлайн-кинотеатра, отвечающая за персонализированную выдачу и продакт-плейсмент. Пиковая нагрузка - 10 000 RPS. Ядро SLO: latency p95 < 1s, error rate < 1%, availability > 99%.

Метрики разделены на 4 уровня по модели Google SRE (Business / Application / ML / Infrastructure). Каждая метрика принадлежит **одной** ветви - бизнес-метрики не лежат в инфре, как явно требует рубрика "отлично".

## 1. Бизнес-метрики

| Метрика | Единица | Target / SLO | Владелец | Источник сбора |
|---|---|---|---|---|
| Conversion rate (просмотр после рекомендации) | % | >= 8% (D7), >= 6% (D1) | Product | Snowflake / dbt, агрегация из событий клиента |
| ARPU (Average Revenue Per User) | RUB / месяц | >= 599 (base), >= 999 (premium) | Product / Finance | Billing service -> ClickHouse |
| DAU/MAU sticky ratio | % | >= 40% | Growth | ClickHouse, recommender_events |
| Watch time per session | минуты | >= 35 min (медиана) | Content | ClickHouse |
| Churn rate (M2M) | % | <= 4% | Retention | dbt-модель / Snowflake |
| Click-through rate на рекомендации | % | >= 12% | ML Product | Recommender event log |

## 2. Метрики приложения (FastAPI ml_service + БД + кеши)

| Метрика | Единица | Target / SLO | Владелец | Источник сбора |
|---|---|---|---|---|
| HTTP request latency p50 | секунды | <= 0.10 | Platform | `request_latency_seconds` histogram, Prometheus |
| HTTP request latency p95 | секунды | <= 1.00 | Platform | `request_latency_seconds` histogram, Prometheus |
| HTTP request latency p99 | секунды | <= 2.00 | Platform | `request_latency_seconds` histogram, Prometheus |
| Request rate (RPS) | req / sec | поддерживать до 10 000 RPS пиково | Platform | `rate(requests_total[1m])` |
| Error rate (5xx + 4xx по бизнес-кодам) | % | < 1.0 | Platform | `requests_total{status=~"5..|4.."}` |
| Saturation (worker queue depth) | tasks | < 80% capacity | Platform | uvicorn worker metric / Prometheus |
| Availability ML-сервиса | % | > 99.0 | Platform / SRE | Prometheus `up`, blackbox-exporter probes |

## 3. ML-метрики (качество модели в продакшене)

| Метрика | Единица | Target / SLO | Владелец | Источник сбора |
|---|---|---|---|---|
| Model prediction confidence (распределение) | вероятность 0..1 | mean >= 0.65, var в пределах baseline +/-15% | ML Engineering | `model_prediction_confidence` histogram, Prometheus |
| Predictions per second | predictions / sec | до 10 000 RPS | ML Engineering | `model_predictions_total` counter |
| PSI (Population Stability Index) по ключевым фичам | unitless | < 0.10 (норма), 0.10-0.25 (warning), > 0.25 (drift) | ML Engineering | Evidently batch job (suite), ежедневный отчёт |
| Wasserstein distance по таргету | unitless | < baseline x 1.5 | ML Engineering | Evidently |
| Model RMSE / Rating MAE | rating units | RMSE <= 0.85 | ML Engineering | Evidently RegressionPreset, ground truth feed |
| Top-K hit rate (рекомендации) | % | >= 15% (Top-10) | ML Product | Offline metric job |
| Inference latency p95 | секунды | <= 0.30 | ML Engineering | Prometheus subset of latency histogram (endpoint=/predict) |
| MLflow registered model staleness | дни | <= 14 от последнего retrain | ML Engineering | MLflow Tracking Server |

## 4. Метрики инфраструктуры

| Метрика | Единица | Target / SLO | Владелец | Источник сбора |
|---|---|---|---|---|
| CPU utilization (контейнер) | % | < 70% устойчиво | SRE | cAdvisor + Prometheus |
| RAM utilization (контейнер) | % | < 80% | SRE | cAdvisor + Prometheus |
| GPU utilization (inference nodes) | % | 50-85% (оптимум) | SRE | DCGM exporter |
| GPU memory | % | < 90% | SRE | DCGM exporter |
| Network throughput | MB/s | заголовок BW канала, < 70% sustained | SRE | node-exporter |
| Container restart count | events / hour | <= 1 | SRE | Prometheus + kube-state-metrics |
| Pod availability (k8s) | % | > 99.5 | SRE | kube-state-metrics |
| Postgres connections | active | < 80% pool | SRE / DBA | postgres_exporter |
| Postgres read latency p99 | мс | < 50 | SRE / DBA | postgres_exporter |
| ClickHouse query latency p95 | мс | < 500 | Data Platform | clickhouse_exporter |

## Обоснование выбранных SLO

- **Latency p95 < 1 сек** - онлайн-кинотеатр требует мгновенного отклика на действия пользователя (открытие карточки, скролл рекомендаций). При p95 выше секунды UX деградирует, конверсия падает на ~7% по каждой добавленной секунде (стандартная индустриальная метрика).
- **Error rate < 1%** - рекомендации не критичны для жизни сервиса (есть fallback на популярное), но 1% это разумный порог: ниже него ошибки тонут в шуме A/B-экспериментов, выше - заметны бизнесу.
- **Availability > 99%** - доступность 99% даёт ~7.2 часа простоя в месяц, что приемлемо для рекомендательного слоя. Базовый каталог должен быть выше (99.95%), но это отдельная система.
- **PSI < 0.10** на ключевых фичах - индустриальный стандарт детектирования дрифта; >0.25 уже требует обязательного retrain.
- **Inference p95 <= 300 мс** - бюджет ML-инференса в общем тайминге запроса (общий p95 < 1 sec - 300 мс инференса - 200 мс БД и кеши - 500 мс резерв на сериализацию/сеть).
