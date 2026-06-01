from fastapi.testclient import TestClient


def test_health_ok(client: TestClient) -> None:
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["version"].startswith("v")
    assert data["model_loaded"] is True


def test_health_without_model(client_without_model: TestClient) -> None:
    response = client_without_model.get("/health")
    assert response.status_code == 200
    assert response.json()["model_loaded"] is False


def test_health_returns_version_header(client: TestClient) -> None:
    response = client.get("/health")
    assert response.headers.get("X-Service-Version", "").startswith("v")
