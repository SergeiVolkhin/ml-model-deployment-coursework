"""Обучение RandomForest + полный MLflow tracking."""
import json
from pathlib import Path

import joblib
import matplotlib.pyplot as plt
import mlflow
import mlflow.sklearn
import pandas as pd
import seaborn as sns
import yaml
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import (
    accuracy_score,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
)

ROOT = Path(__file__).resolve().parents[1]
PROCESSED = ROOT / "data" / "processed"
MODELS = ROOT / "models"
TARGET = "wine_class"


def main() -> None:
    params = yaml.safe_load((ROOT / "params.yaml").read_text(encoding="utf-8"))
    train_p = params["train"]
    prepare_p = params["prepare"]

    # грузим сплиты
    train_df = pd.read_csv(PROCESSED / "train.csv")
    test_df = pd.read_csv(PROCESSED / "test.csv")
    X_train, y_train = train_df.drop(columns=[TARGET]), train_df[TARGET]
    X_test, y_test = test_df.drop(columns=[TARGET]), test_df[TARGET]

    # MLflow трекинг в локальную sqlite
    mlflow.set_tracking_uri(f"sqlite:///{ROOT / 'mlflow.db'}")
    mlflow.set_experiment("wine-classification")

    with mlflow.start_run():
        # все гиперпараметры из params.yaml
        mlflow.log_params(train_p)
        mlflow.log_param("test_size", prepare_p["test_size"])
        mlflow.log_param("split_random_state", prepare_p["random_state"])

        # обучаем RF
        model = RandomForestClassifier(
            n_estimators=train_p["n_estimators"],
            max_depth=train_p["max_depth"],
            random_state=train_p["random_state"],
        )
        model.fit(X_train, y_train)
        y_pred = model.predict(X_test)

        # метрики на test
        metrics = {
            "accuracy": accuracy_score(y_test, y_pred),
            "f1_macro": f1_score(y_test, y_pred, average="macro"),
            "precision_macro": precision_score(y_test, y_pred, average="macro"),
            "recall_macro": recall_score(y_test, y_pred, average="macro"),
        }
        mlflow.log_metrics(metrics)
        for k, v in metrics.items():
            print(f"{k}: {v:.4f}")

        # сохраняем модель локально (для DVC) + логируем как артефакт MLflow
        MODELS.mkdir(parents=True, exist_ok=True)
        model_path = MODELS / "model.pkl"
        joblib.dump(model, model_path)
        mlflow.log_artifact(str(model_path))

        # confusion matrix - визуализируем и логируем
        cm = confusion_matrix(y_test, y_pred)
        fig, ax = plt.subplots(figsize=(5, 4))
        sns.heatmap(cm, annot=True, fmt="d", cmap="Blues", ax=ax)
        ax.set_xlabel("predicted")
        ax.set_ylabel("actual")
        ax.set_title("Wine confusion matrix")
        cm_path = ROOT / "confusion_matrix.png"
        fig.tight_layout()
        fig.savefig(cm_path, dpi=120)
        plt.close(fig)
        mlflow.log_artifact(str(cm_path))

        # бонус - логируем sklearn-модель чтобы потом можно было через mlflow.sklearn.load_model
        mlflow.sklearn.log_model(model, name="rf_model")

        # метрики для DVC
        (ROOT / "metrics.json").write_text(json.dumps(metrics, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
