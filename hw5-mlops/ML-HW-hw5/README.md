# MLOps HW5 - Volkhin Sergei

ML pipeline с версионированием данных (DVC), отслеживанием экспериментов (MLflow) и Feature Store (Feast + PostgreSQL).

## Цель

Воспроизводимый ML-контур для классификации вин (Wine dataset, 3 класса, 13 фичей) с полным MLOps-стеком: данные под DVC, эксперименты в MLflow, фичи в Feast/Postgres.

## Структура

```
.
├── data/
│   ├── raw/wine.csv         # под DVC
│   └── processed/           # train.csv, test.csv (output prepare)
├── src/
│   ├── prepare.py           # сплит данных
│   ├── train.py             # RF + MLflow logging
│   └── feature_store/
│       ├── feature_store.yaml
│       ├── definitions.py
│       └── load_to_postgres.py
├── notebooks/
│   ├── marimo_example.py
│   └── analysis.md          # сравнение ipynb vs Marimo
├── docs/
│   ├── ml_system_readiness.md
│   └── face_blur_architecture.md
├── models/model.pkl         # output train (под DVC)
├── docker-compose.yml       # postgres для Feast
├── dvc.yaml
├── params.yaml
├── requirements.txt
├── metrics.json             # метрики DVC
└── HW5_MLOps_Вольхин_Сергей.ipynb  # сводный отчёт по 6 разделам ДЗ
```

## Быстрый старт

```bash
git clone -b hw5 git@github.com:SergeiVolkhin/ML-HW.git
cd ML-HW
python -m venv .venv && source .venv/Scripts/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
dvc pull
dvc repro
```

После `dvc repro` появятся: `data/processed/`, `models/model.pkl`, `confusion_matrix.png`, `metrics.json`, `mlflow.db`.

## Pipeline

| Стадия | Команда | Вход | Выход |
|---|---|---|---|
| `prepare` | `python src/prepare.py` | `data/raw/wine.csv`, `params.prepare` | `data/processed/{train,test}.csv` |
| `train` | `python src/train.py` | `data/processed/`, `params.train` | `models/model.pkl`, `confusion_matrix.png`, `metrics.json` + MLflow run |

Изменение любого `params.yaml`-параметра в секции `prepare`/`train` инвалидирует соответствующие стадии. `dvc repro` пересчитает только что изменилось.

## MLflow UI

```bash
mlflow ui --backend-store-uri sqlite:///mlflow.db
```

Открыть http://localhost:5000. Эксперимент `wine-classification` содержит run с:
- params: `n_estimators`, `max_depth`, `random_state`, `model_type`, `test_size`, `split_random_state`
- metrics: `accuracy`, `f1_macro`, `precision_macro`, `recall_macro`
- artifacts: `model.pkl`, `confusion_matrix.png`, sklearn-модель в формате MLflow (под `rf_model/`)

## Feature Store (Feast + PostgreSQL)

Postgres поднимается через docker-compose (порт хоста 5433, чтобы не конфликтовать с локальным сервером).

```bash
# 1. поднимаем postgres
docker compose up -d postgres

# 2. грузим wine dataset в таблицу wine_features
python src/feature_store/load_to_postgres.py

# 3. регистрируем определения фичей
cd src/feature_store
feast apply

# 4. материализуем в online store
feast materialize-incremental "$(date -u +%Y-%m-%dT%H:%M:%S)"

# 5. проверяем что фичи отдаются на эндпоинте
feast feature-views list
feast feature-services list
```

Online retrieval из python:

```python
from feast import FeatureStore
fs = FeatureStore(repo_path="src/feature_store")
features = fs.get_online_features(
    features=["wine_features:alcohol", "wine_features:proline", "wine_features:wine_class"],
    entity_rows=[{"wine_id": 0}, {"wine_id": 50}],
).to_dict()
```

Конфигурация:
- registry: SQL в Postgres (`registry_type: sql`)
- offline_store / online_store: оба `type: postgres` (требование критерия)

## DVC remote

Локальный remote в `./.dvc-storage/` (default). Для общего использования замените на S3/GCS:

```bash
dvc remote modify --local local-storage url s3://my-bucket/dvc
dvc remote modify --local local-storage --add credentialpath ~/.aws/credentials
```

`dvc push` после каждого коммита, `dvc pull` после клона.

## Что зачем (по критериям ДЗ)

| Критерий | Где |
|---|---|
| Сводный отчёт ipynb | `HW5_MLOps_Вольхин_Сергей.ipynb` |
| ipynb vs Marimo | `notebooks/analysis.md`, `notebooks/marimo_example.py` |
| DVC: add + .dvc + remote | `data/raw/wine.csv.dvc`, `.dvc/config`, `./.dvc-storage/` |
| Feature Store (postgres template) | `src/feature_store/feature_store.yaml`, `definitions.py` |
| MLflow params + metrics + artifacts | `src/train.py` (log_params, log_metrics, log_artifact x2 + log_model) |
| Face blur схема со слоями | `docs/face_blur_architecture.md` |
| Готовность ML-системы к проду | `docs/ml_system_readiness.md` |

## Воспроизводимость

После `git clone -b hw5 ... && pip install -r requirements.txt && dvc pull && dvc repro` метрики в `metrics.json` совпадают с зафиксированными в репо (random_state=42 везде).

## Полезные команды

```bash
dvc repro            # пересчитать пайплайн с учетом изменений
dvc repro --force    # пересчитать всё с нуля
dvc metrics show     # таблица метрик
dvc params diff      # diff параметров между коммитами
dvc dag              # граф пайплайна
docker compose down  # остановить postgres
```
