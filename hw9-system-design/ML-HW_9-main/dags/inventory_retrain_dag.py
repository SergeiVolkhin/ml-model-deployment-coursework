"""
DAG переобучения модели прогноза складских запасов сетевого магазина.

Архитектура: батч + event-driven триггер.
- Расписание @hourly как страховка: даже если внешний триггер не сработает,
  DAG поднимется сам и проверит условия переобучения.
- Дешевле и проще стриминга: латентность секунд для прогноза остатков не нужна,
  важна свежесть фичей и реакция на накопление чеков.

Логика принятия решения о переобучении (любое из трёх условий):
1. На S3 за сутки накоплено более MIN_CHECKS_THRESHOLD чеков (читаем манифест,
   а не сами файлы, чтобы не тратить I/O).
2. Текущая accuracy production-модели в MLflow упала ниже ACCURACY_THRESHOLD.
3. До истечения valid_until production-модели осталось менее MODEL_TTL_HOURS.

Защита от деградации: новая модель промоутится в Production только если её MAE
строго меньше production-MAE (ShortCircuitOperator). Иначе обучение прошло,
артефакт сохранён, но переключения нет.

Зависимости тасков (схема в конце файла).
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any

import mlflow
import numpy as np
import pandas as pd
from airflow import DAG
from airflow.exceptions import AirflowFailException
from airflow.operators.empty import EmptyOperator
from airflow.operators.python import (
    BranchPythonOperator,
    PythonOperator,
    ShortCircuitOperator,
)
from airflow.providers.amazon.aws.hooks.s3 import S3Hook
from airflow.providers.amazon.aws.sensors.s3 import S3KeySensor
from airflow.utils.task_group import TaskGroup
from mlflow.tracking import MlflowClient
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_absolute_error

# --------------------------------------------------------------------------- #
# Константы конфигурации (никаких магических чисел в теле тасков).
# --------------------------------------------------------------------------- #
S3_BUCKET: str = "retail-checks"
S3_RAW_PREFIX: str = "raw/{{ ds }}/"
S3_MANIFEST_KEY: str = "raw/{{ ds }}/manifest.json"

MLFLOW_TRACKING_URI: str = "http://mlflow:5000"
MLFLOW_EXPERIMENT: str = "inventory-forecast"
MLFLOW_MODEL_NAME: str = "inventory_forecast"

MIN_CHECKS_THRESHOLD: int = 10_000_000
ACCURACY_THRESHOLD: float = 0.85
MODEL_TTL_HOURS: int = 1
MAE_THRESHOLD: float = 15.0

DAG_ID: str = "inventory_retrain_pipeline"
S3_POKE_INTERVAL_S: int = 300
S3_TIMEOUT_S: int = 3600
TASK_TIMEOUT_MIN: int = 30

LOG = logging.getLogger(__name__)


# --------------------------------------------------------------------------- #
# Колбэки и вспомогательные структуры.
# --------------------------------------------------------------------------- #
def _failure_alert(context: dict[str, Any]) -> None:
    """Хук для алертов в Slack / PagerDuty. Заглушка пишет в лог."""
    task_id = context["task_instance"].task_id
    dag_id = context["task_instance"].dag_id
    LOG.error("DAG %s task %s упал, run %s", dag_id, task_id, context["run_id"])


default_args: dict[str, Any] = {
    "owner": "ml-platform",
    "depends_on_past": False,
    "email": ["ml-oncall@example.com"],
    "email_on_failure": True,
    "email_on_retry": False,
    "retries": 2,
    "retry_delay": timedelta(minutes=5),
    "execution_timeout": timedelta(minutes=TASK_TIMEOUT_MIN),
    "on_failure_callback": _failure_alert,
}


@dataclass(frozen=True)
class ProductionModelState:
    """Снимок состояния production-модели для решения о переобучении."""

    version: int
    accuracy: float
    mae: float
    valid_until: datetime


# --------------------------------------------------------------------------- #
# Логика принятия решения о переобучении.
# --------------------------------------------------------------------------- #
def _read_manifest_total_checks(execution_date: str) -> int:
    """Достаёт суммарный счётчик чеков из manifest.json на S3."""
    hook = S3Hook(aws_conn_id="aws_default")
    key = f"raw/{execution_date}/manifest.json"
    raw = hook.read_key(key=key, bucket_name=S3_BUCKET)
    manifest = json.loads(raw)
    total = int(manifest.get("total_checks", 0))
    LOG.info("manifest %s: total_checks=%s", key, total)
    return total


def _fetch_production_state() -> ProductionModelState | None:
    """Тянет метаданные production-модели из Model Registry MLflow."""
    mlflow.set_tracking_uri(MLFLOW_TRACKING_URI)
    client = MlflowClient()
    versions = client.get_latest_versions(name=MLFLOW_MODEL_NAME, stages=["Production"])
    if not versions:
        LOG.warning("в Registry нет production-версии модели %s", MLFLOW_MODEL_NAME)
        return None
    mv = versions[0]
    run = client.get_run(mv.run_id)
    valid_until_raw = mv.tags.get("valid_until")
    if valid_until_raw is None:
        LOG.warning("у production-версии нет тега valid_until, считаем что истекает сразу")
        valid_until = datetime.now(tz=timezone.utc)
    else:
        valid_until = datetime.fromisoformat(valid_until_raw)
    return ProductionModelState(
        version=int(mv.version),
        accuracy=float(run.data.metrics.get("accuracy", 0.0)),
        mae=float(run.data.metrics.get("mae", float("inf"))),
        valid_until=valid_until,
    )


def decide_retrain(**context: Any) -> str:
    """Возвращает task_id следующего таска: либо training, либо skip."""
    ds = context["ds"]
    total_checks = _read_manifest_total_checks(ds)
    state = _fetch_production_state()

    reasons: list[str] = []
    if total_checks > MIN_CHECKS_THRESHOLD:
        reasons.append(f"total_checks={total_checks} > {MIN_CHECKS_THRESHOLD}")

    if state is None:
        reasons.append("production-модель отсутствует в Registry")
    else:
        if state.accuracy < ACCURACY_THRESHOLD:
            reasons.append(f"accuracy={state.accuracy:.3f} < {ACCURACY_THRESHOLD}")
        ttl_left = state.valid_until - datetime.now(tz=timezone.utc)
        if ttl_left < timedelta(hours=MODEL_TTL_HOURS):
            reasons.append(f"valid_until через {ttl_left}, порог {MODEL_TTL_HOURS}h")

    if reasons:
        LOG.info("запускаем переобучение, причины: %s", "; ".join(reasons))
        context["ti"].xcom_push(key="retrain_reasons", value=reasons)
        return "training.extract_features"

    LOG.info("условия не выполнены, переобучение пропускается")
    return "skip_training"


# --------------------------------------------------------------------------- #
# Таски TaskGroup training.
# --------------------------------------------------------------------------- #
def extract_features(**context: Any) -> str:
    """Читает сырые чеки за период, агрегирует в фичи, кладёт parquet на S3."""
    ds = context["ds"]
    hook = S3Hook(aws_conn_id="aws_default")
    keys = hook.list_keys(bucket_name=S3_BUCKET, prefix=f"raw/{ds}/")
    LOG.info("найдено %s сырых файлов за %s", len(keys or []), ds)
    # Заглушка: реальная агрегация шла бы Spark/DuckDB, здесь демонстрация контракта.
    out_key = f"features/{ds}/features.parquet"
    LOG.info("фичи будут сохранены в s3://%s/%s", S3_BUCKET, out_key)
    return out_key


def _make_synthetic_dataset(n_periods: int = 180, seed: int = 42) -> pd.DataFrame:
    """Синтетический убывающий остаток с гауссовским шумом - заглушка для демонстрации."""
    rng = np.random.default_rng(seed)
    base = np.arange(n_periods, 0, -1, dtype=float)
    noise = rng.normal(loc=0.0, scale=1.0, size=n_periods)
    stock = base + noise
    return pd.DataFrame({"day_index": np.arange(n_periods), "stock_remaining": stock})


def train_model(**context: Any) -> dict[str, float]:
    """Обучает LinearRegression на убывающем остатке, логирует артефакты в MLflow."""
    mlflow.set_tracking_uri(MLFLOW_TRACKING_URI)
    mlflow.set_experiment(MLFLOW_EXPERIMENT)
    run_name = f"inventory-{context['ds']}-{context['ts_nodash']}"

    df = _make_synthetic_dataset()
    x = df[["day_index"]].to_numpy()
    y = df["stock_remaining"].to_numpy()
    split = int(0.8 * len(df))

    with mlflow.start_run(run_name=run_name) as run:
        model = LinearRegression()
        model.fit(x[:split], y[:split])
        preds = model.predict(x[split:])
        mae = float(mean_absolute_error(y[split:], preds))

        mlflow.log_param("model", "LinearRegression")
        mlflow.log_param("n_train", split)
        mlflow.log_param("n_test", len(df) - split)
        mlflow.log_metric("mae", mae)
        mlflow.sklearn.log_model(model, artifact_path="model")
        run_id = run.info.run_id

    LOG.info("train_model finished: run_id=%s mae=%.3f", run_id, mae)
    return {"run_id": run_id, "mae": mae}


def validate_model(**context: Any) -> None:
    """Падает явно если MAE новой модели хуже порога - защита от регистрации мусора."""
    train_result = context["ti"].xcom_pull(task_ids="training.train_model")
    mae = float(train_result["mae"])
    if mae > MAE_THRESHOLD:
        raise AirflowFailException(f"MAE={mae:.3f} превышает порог {MAE_THRESHOLD}")
    LOG.info("валидация пройдена: MAE=%.3f <= %.3f", mae, MAE_THRESHOLD)


def register_in_mlflow(**context: Any) -> int:
    """Регистрирует модель в Model Registry со стадией Staging."""
    train_result = context["ti"].xcom_pull(task_ids="training.train_model")
    run_id = train_result["run_id"]

    mlflow.set_tracking_uri(MLFLOW_TRACKING_URI)
    client = MlflowClient()
    model_uri = f"runs:/{run_id}/model"
    mv = mlflow.register_model(model_uri=model_uri, name=MLFLOW_MODEL_NAME)
    client.transition_model_version_stage(
        name=MLFLOW_MODEL_NAME,
        version=mv.version,
        stage="Staging",
        archive_existing_versions=False,
    )
    client.set_model_version_tag(
        name=MLFLOW_MODEL_NAME,
        version=mv.version,
        key="valid_until",
        value=(datetime.now(tz=timezone.utc) + timedelta(days=7)).isoformat(),
    )
    LOG.info("зарегистрирована версия %s в Staging", mv.version)
    return int(mv.version)


# --------------------------------------------------------------------------- #
# Сравнение с production и промоушн.
# --------------------------------------------------------------------------- #
def is_new_model_better(**context: Any) -> bool:
    """True если новая модель строго лучше production по MAE."""
    train_result = context["ti"].xcom_pull(task_ids="training.train_model")
    new_mae = float(train_result["mae"])

    state = _fetch_production_state()
    if state is None:
        LOG.info("production отсутствует, промоутим новую (MAE=%.3f)", new_mae)
        return True

    better = new_mae < state.mae
    LOG.info(
        "сравнение моделей: new_mae=%.3f, prod_mae=%.3f -> promote=%s",
        new_mae,
        state.mae,
        better,
    )
    return better


def promote_to_production(**context: Any) -> None:
    """Переводит новую версию в стадию Production, архивируя предыдущую."""
    new_version = context["ti"].xcom_pull(task_ids="training.register_in_mlflow")
    mlflow.set_tracking_uri(MLFLOW_TRACKING_URI)
    client = MlflowClient()
    client.transition_model_version_stage(
        name=MLFLOW_MODEL_NAME,
        version=new_version,
        stage="Production",
        archive_existing_versions=True,
    )
    LOG.info("версия %s переведена в Production", new_version)


def notify(**context: Any) -> None:
    """Финальная нотификация - в реальности слала бы в Slack/Webhook."""
    reasons = context["ti"].xcom_pull(task_ids="decide_retrain", key="retrain_reasons")
    LOG.info("DAG завершён, причины переобучения: %s", reasons or "skip")


# --------------------------------------------------------------------------- #
# Описание графа.
# --------------------------------------------------------------------------- #
with DAG(
    dag_id=DAG_ID,
    description="Continuous training pipeline для прогноза складских запасов",
    start_date=datetime(2025, 1, 1, tzinfo=timezone.utc),
    schedule="@hourly",
    catchup=False,
    max_active_runs=1,
    default_args=default_args,
    tags=["ml", "inventory", "retraining"],
    doc_md=__doc__,
) as dag:

    wait_s3 = S3KeySensor(
        task_id="wait_s3",
        bucket_name=S3_BUCKET,
        bucket_key=S3_MANIFEST_KEY,
        aws_conn_id="aws_default",
        poke_interval=S3_POKE_INTERVAL_S,
        timeout=S3_TIMEOUT_S,
        mode="reschedule",
    )

    decide = BranchPythonOperator(
        task_id="decide_retrain",
        python_callable=decide_retrain,
    )

    skip = EmptyOperator(task_id="skip_training")

    with TaskGroup(group_id="training") as training:
        t_extract = PythonOperator(
            task_id="extract_features",
            python_callable=extract_features,
        )
        t_train = PythonOperator(
            task_id="train_model",
            python_callable=train_model,
        )
        t_validate = PythonOperator(
            task_id="validate_model",
            python_callable=validate_model,
        )
        t_register = PythonOperator(
            task_id="register_in_mlflow",
            python_callable=register_in_mlflow,
        )
        t_extract >> t_train >> t_validate >> t_register

    gate = ShortCircuitOperator(
        task_id="is_new_model_better",
        python_callable=is_new_model_better,
        ignore_downstream_trigger_rules=False,
    )

    promote = PythonOperator(
        task_id="promote_to_production",
        python_callable=promote_to_production,
    )

    final_notify = PythonOperator(
        task_id="notify",
        python_callable=notify,
        trigger_rule="none_failed_min_one_success",
    )

    wait_s3 >> decide
    decide >> training >> gate >> promote >> final_notify
    decide >> skip >> final_notify


# ASCII-схема графа:
#
#   wait_s3
#      |
#   decide_retrain (branch)
#      |---------- skip_training -----------+
#      |                                     |
#      v                                     |
#   training (TaskGroup)                     |
#      extract_features                      |
#         -> train_model                     |
#         -> validate_model                  |
#         -> register_in_mlflow              |
#      |                                     |
#      v                                     |
#   is_new_model_better (short-circuit)      |
#      |                                     |
#      v                                     |
#   promote_to_production                    |
#      |                                     |
#      +----------> notify <-----------------+
