from fastapi.testclient import TestClient
from fraud_platform_api.main import build_app


def test_api_live_health() -> None:
    client = TestClient(build_app())
    response = client.get("/health/live")
    assert response.status_code == 200
    assert response.json()["status"] == "live"


def test_api_root_metadata() -> None:
    client = TestClient(build_app())
    response = client.get("/")
    assert response.status_code == 200
    assert response.json()["service"] == "api"
