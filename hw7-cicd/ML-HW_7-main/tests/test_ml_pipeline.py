import json
import sys
from pathlib import Path

import joblib
import numpy as np
import pytest
from sklearn.datasets import load_iris

from app import ml_pipeline


def test_train_creates_model_file(tmp_path: Path) -> None:
    model_path = tmp_path / "model.pkl"
    ml_pipeline.train(model_path, random_state=42, hyperparams=ml_pipeline.DEFAULT_HYPERPARAMS)

    assert model_path.exists()
    model = joblib.load(model_path)
    assert hasattr(model, "predict")


def test_train_returns_metrics(tmp_path: Path) -> None:
    metrics = ml_pipeline.train(
        tmp_path / "model.pkl", random_state=42, hyperparams=ml_pipeline.DEFAULT_HYPERPARAMS
    )

    expected_keys = {
        "train_accuracy",
        "test_accuracy",
        "random_state",
        "hyperparameters",
        "n_train",
        "n_test",
    }
    assert expected_keys.issubset(metrics.keys())
    assert 0.0 <= metrics["train_accuracy"] <= 1.0
    assert 0.0 <= metrics["test_accuracy"] <= 1.0
    assert metrics["random_state"] == 42
    assert metrics["n_train"] == 120
    assert metrics["n_test"] == 30


def test_train_is_reproducible(tmp_path: Path) -> None:
    path_a = tmp_path / "a.pkl"
    path_b = tmp_path / "b.pkl"

    ml_pipeline.train(path_a, random_state=42, hyperparams=ml_pipeline.DEFAULT_HYPERPARAMS)
    ml_pipeline.train(path_b, random_state=42, hyperparams=ml_pipeline.DEFAULT_HYPERPARAMS)

    model_a = joblib.load(path_a)
    model_b = joblib.load(path_b)
    iris = load_iris()
    assert np.array_equal(model_a.predict(iris.data), model_b.predict(iris.data))


def test_main_writes_metrics(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    model_path = tmp_path / "model.pkl"
    metrics_path = tmp_path / "metrics.json"
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "ml_pipeline",
            "--output-path",
            str(model_path),
            "--random-state",
            "7",
            "--metrics-path",
            str(metrics_path),
        ],
    )

    ml_pipeline.main()

    assert model_path.exists()
    assert metrics_path.exists()
    payload = json.loads(metrics_path.read_text())
    assert payload["random_state"] == 7
    assert payload["hyperparameters"] == ml_pipeline.DEFAULT_HYPERPARAMS
