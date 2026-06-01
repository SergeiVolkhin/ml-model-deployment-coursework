from fastapi.testclient import TestClient


def test_predict_valid_setosa(client: TestClient) -> None:
    response = client.post("/predict", json={"x": [5.1, 3.5, 1.4, 0.2]})
    assert response.status_code == 200
    data = response.json()
    assert data["prediction"] in {0, 1, 2}
    assert data["class_name"] in {"setosa", "versicolor", "virginica"}
    assert data["version"].startswith("v")


def test_predict_setosa_class(client: TestClient) -> None:
    response = client.post("/predict", json={"x": [5.1, 3.5, 1.4, 0.2]})
    assert response.json()["class_name"] == "setosa"


def test_predict_wrong_length_returns_422(client: TestClient) -> None:
    response = client.post("/predict", json={"x": [5.1, 3.5, 1.4]})
    assert response.status_code == 422


def test_predict_non_numeric_returns_422(client: TestClient) -> None:
    response = client.post("/predict", json={"x": [5.1, "three", 1.4, 0.2]})
    assert response.status_code == 422


def test_predict_missing_field_returns_422(client: TestClient) -> None:
    response = client.post("/predict", json={})
    assert response.status_code == 422


def test_predict_without_model_returns_503(client_without_model: TestClient) -> None:
    response = client_without_model.post("/predict", json={"x": [5.1, 3.5, 1.4, 0.2]})
    assert response.status_code == 503
    assert response.json()["detail"] == "model is not loaded"
