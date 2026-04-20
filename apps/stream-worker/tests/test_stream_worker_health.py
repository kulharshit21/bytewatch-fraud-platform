from fastapi.testclient import TestClient
from fraud_platform_stream_worker.main import build_app


def test_stream_worker_health_endpoint() -> None:
    client = TestClient(build_app())
    response = client.get("/health/live")
    assert response.status_code == 200
    assert response.json()["service"] == "stream-worker"
