from fastapi.testclient import TestClient
from fraud_platform_producer.main import build_app


def test_producer_health_endpoint() -> None:
    client = TestClient(build_app())
    response = client.get("/health/live")
    assert response.status_code == 200
    assert response.json()["service"] == "producer"
