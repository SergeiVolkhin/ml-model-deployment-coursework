from pathlib import Path

import joblib
import pytest
from fastapi.testclient import TestClient
from sklearn.datasets import load_iris
from sklearn.ensemble import RandomForestClassifier


@pytest.fixture(scope="session")
def trained_model_path(tmp_path_factory: pytest.TempPathFactory) -> Path:
    iris = load_iris()
    model = RandomForestClassifier(n_estimators=20, random_state=42)
    model.fit(iris.data, iris.target)
    path = tmp_path_factory.mktemp("models") / "model.pkl"
    joblib.dump(model, path)
    return path


@pytest.fixture
def client(monkeypatch: pytest.MonkeyPatch, trained_model_path: Path) -> TestClient:
    monkeypatch.setenv("MODEL_PATH", str(trained_model_path))
    monkeypatch.setenv("MODEL_VERSION", "v1.0.0")

    import importlib

    from app import main as app_main

    importlib.reload(app_main)
    with TestClient(app_main.app) as test_client:
        yield test_client


@pytest.fixture
def client_without_model(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> TestClient:
    missing = tmp_path / "missing.pkl"
    monkeypatch.setenv("MODEL_PATH", str(missing))
    monkeypatch.setenv("MODEL_VERSION", "v1.0.0")

    import importlib

    from app import main as app_main

    importlib.reload(app_main)
    with TestClient(app_main.app) as test_client:
        yield test_client
