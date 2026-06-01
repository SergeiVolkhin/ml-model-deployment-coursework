import argparse
import json
import logging
from pathlib import Path

import joblib
from sklearn.datasets import load_iris
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score
from sklearn.model_selection import train_test_split

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("train")

DEFAULT_HYPERPARAMS = {"n_estimators": 100, "max_depth": None}


def train(output_path: Path, random_state: int, hyperparams: dict) -> dict:
    iris = load_iris()
    x_train, x_test, y_train, y_test = train_test_split(
        iris.data, iris.target, test_size=0.2, random_state=random_state, stratify=iris.target
    )

    model = RandomForestClassifier(random_state=random_state, **hyperparams)
    model.fit(x_train, y_train)

    train_accuracy = accuracy_score(y_train, model.predict(x_train))
    test_accuracy = accuracy_score(y_test, model.predict(x_test))

    output_path.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(model, output_path)

    logger.info("train accuracy: %.4f", train_accuracy)
    logger.info("test accuracy: %.4f", test_accuracy)
    logger.info("model saved to %s", output_path)

    return {
        "train_accuracy": train_accuracy,
        "test_accuracy": test_accuracy,
        "random_state": random_state,
        "hyperparameters": hyperparams,
        "n_train": len(x_train),
        "n_test": len(x_test),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Train RandomForest on iris dataset")
    parser.add_argument(
        "--output-path",
        type=Path,
        default=Path("app/models/model.pkl"),
        help="Куда сохранить обученную модель",
    )
    parser.add_argument(
        "--random-state",
        type=int,
        default=42,
        help="Random seed для воспроизводимости",
    )
    parser.add_argument(
        "--metrics-path",
        type=Path,
        default=None,
        help="Опциональный JSON с метриками обучения",
    )
    args = parser.parse_args()

    metrics = train(args.output_path, args.random_state, DEFAULT_HYPERPARAMS)

    if args.metrics_path is not None:
        args.metrics_path.parent.mkdir(parents=True, exist_ok=True)
        args.metrics_path.write_text(json.dumps(metrics, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
