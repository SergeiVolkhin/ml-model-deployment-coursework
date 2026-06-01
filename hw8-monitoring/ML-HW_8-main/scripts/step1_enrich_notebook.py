"""One-shot script: copy template notebook to notebook/ under the new name and enrich cell 1 with the metrics tree (Step 1 of HW8)."""
import shutil
from pathlib import Path

import nbformat

REPO_ROOT = Path(r"C:\Python\ML HW\8")
TEMPLATE = REPO_ROOT / "HW8_Monitoring_Фамилия_Имя.ipynb"
TARGET_DIR = REPO_ROOT / "notebook"
TARGET = TARGET_DIR / "HW8_Monitoring_Volkhin_Sergei.ipynb"

METRICS_TREE_MARKDOWN = """

## Дерево метрик ML-системы

Контекст системы: рекомендательная ML-платформа онлайн-кинотеатра, пиковая нагрузка 10 000 RPS, ключевые SLO - latency p95 < 1s, error rate < 1%, availability > 99%.

Полный текст с владельцами и источниками сбора - в `docs/metrics_tree.md`. Здесь компактная сводка по четырём ветвям.

### Бизнес-метрики

| Метрика | Единица | Target / SLO | Владелец | Источник |
|---|---|---|---|---|
| Conversion rate (просмотр после рекомендации) | % | >= 8% (D7) | Product | Snowflake / dbt |
| ARPU | RUB / месяц | >= 599 base, >= 999 premium | Product / Finance | Billing -> ClickHouse |
| DAU/MAU sticky ratio | % | >= 40% | Growth | ClickHouse |
| Watch time per session | минуты | медиана >= 35 | Content | ClickHouse |
| Churn rate (M2M) | % | <= 4% | Retention | dbt / Snowflake |
| CTR на рекомендации | % | >= 12% | ML Product | Recommender event log |

### Метрики приложения

| Метрика | Единица | Target / SLO | Владелец | Источник |
|---|---|---|---|---|
| HTTP latency p50 / p95 / p99 | секунды | 0.10 / 1.00 / 2.00 | Platform | `request_latency_seconds`, Prometheus |
| Request rate (RPS) | req / s | до 10 000 RPS пиково | Platform | `rate(requests_total[1m])` |
| Error rate | % | < 1.0 | Platform | `requests_total{status=~"5..|4.."}` |
| Saturation (worker queue depth) | tasks | < 80% capacity | Platform | uvicorn / Prometheus |
| Availability ML-сервиса | % | > 99.0 | Platform / SRE | Prometheus `up`, blackbox |

### ML-метрики

| Метрика | Единица | Target / SLO | Владелец | Источник |
|---|---|---|---|---|
| Model prediction confidence | 0..1 | mean >= 0.65, var в +/-15% baseline | ML Engineering | `model_prediction_confidence` histogram |
| Predictions per second | pred / s | до 10 000 | ML Engineering | `model_predictions_total` counter |
| PSI ключевых фич | unitless | < 0.10 норма, 0.10-0.25 warning, > 0.25 drift | ML Engineering | Evidently batch |
| Wasserstein distance таргета | unitless | < baseline x 1.5 | ML Engineering | Evidently |
| Model RMSE / MAE | rating units | RMSE <= 0.85 | ML Engineering | Evidently RegressionPreset |
| Inference latency p95 (только /predict) | секунды | <= 0.30 | ML Engineering | Prometheus subset |
| MLflow model staleness | дни | <= 14 от последнего retrain | ML Engineering | MLflow Tracking |
| Top-K hit rate (Top-10) | % | >= 15 | ML Product | Offline metric job |

### Метрики инфраструктуры

| Метрика | Единица | Target / SLO | Владелец | Источник |
|---|---|---|---|---|
| CPU utilization (контейнер) | % | < 70 sustained | SRE | cAdvisor + Prometheus |
| RAM utilization (контейнер) | % | < 80 | SRE | cAdvisor + Prometheus |
| GPU utilization (inference) | % | 50-85 | SRE | DCGM exporter |
| GPU memory | % | < 90 | SRE | DCGM exporter |
| Container restart count | events / hour | <= 1 | SRE | kube-state-metrics |
| Pod availability (k8s) | % | > 99.5 | SRE | kube-state-metrics |
| Postgres read latency p99 | мс | < 50 | SRE / DBA | postgres_exporter |
| ClickHouse query latency p95 | мс | < 500 | Data Platform | clickhouse_exporter |

### Обоснование SLO

- **Latency p95 < 1 сек** - онлайн-кинотеатр требует мгновенного отклика на действия пользователя; индустриальные исследования показывают падение конверсии примерно на 7% на каждую добавленную секунду задержки.
- **Error rate < 1%** - рекомендации не критичны для жизни сервиса (есть fallback на популярное), ниже 1% ошибки тонут в шуме A/B-экспериментов, выше - заметны бизнесу.
- **Availability > 99%** - 99% даёт около 7.2 часов простоя в месяц, что приемлемо для рекомендательного слоя (базовый каталог требует 99.95%, но это отдельная система с другим SLO).
- **PSI < 0.10** - индустриальный стандарт детектирования дрифта; PSI выше 0.25 уже требует обязательного retrain.
- **Inference p95 <= 300 мс** - бюджет ML-инференса в общем тайминге запроса (1 sec общий p95 минус 300 мс инференса минус 200 мс БД и кеши - остаётся 500 мс резерва на сериализацию и сеть).
"""


def main():
    TARGET_DIR.mkdir(parents=True, exist_ok=True)
    if not TARGET.exists():
        shutil.copyfile(TEMPLATE, TARGET)
        print(f"copied template -> {TARGET}")
    else:
        print(f"target exists, will only patch in-place: {TARGET}")

    nb = nbformat.read(str(TARGET), as_version=4)
    cell1 = nb.cells[1]
    assert cell1.cell_type == "markdown", "cell 1 must be markdown"

    if "## Дерево метрик" in cell1.source:
        print("metrics tree already present, skipping append")
    else:
        cell1.source = cell1.source.rstrip() + "\n" + METRICS_TREE_MARKDOWN
        print(f"appended metrics tree, new cell 1 length: {len(cell1.source)} chars")

    nbformat.write(nb, str(TARGET))
    nbformat.validate(nbformat.read(str(TARGET), as_version=4))
    print("notebook validated OK")


if __name__ == "__main__":
    main()
