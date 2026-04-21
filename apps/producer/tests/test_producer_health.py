from fastapi.testclient import TestClient
from fraud_platform_producer.main import build_app


def test_producer_health_endpoint() -> None:
    client = TestClient(build_app())
    response = client.get("/health/live")
    assert response.status_code == 200
    assert response.json()["service"] == "producer"


def test_producer_control_endpoints(monkeypatch) -> None:
    import fraud_platform_producer.main as producer_main

    class FakeRuntime:
        def __init__(self, settings):
            self.settings = settings
            self.stats = type(
                "Stats",
                (),
                {
                    "running": True,
                    "generated_events": 21,
                    "started_at": None,
                    "current_rate_per_second": 6.0,
                    "current_fraud_ratio": 0.68,
                    "override_expires_at": None,
                },
            )()

        def start(self):
            self.stats.running = True

        def stop(self):
            self.stats.running = False

        def inject_burst(self, *, scenario, events):
            return [
                type("Event", (), {"transaction_id": f"txn_demo_{index}"})()
                for index in range(events)
            ]

        def apply_temporary_profile(
            self,
            *,
            fraud_ratio=None,
            rate_per_second=None,
            duration_seconds=30,
        ):
            self.stats.current_fraud_ratio = fraud_ratio or self.stats.current_fraud_ratio
            self.stats.current_rate_per_second = (
                rate_per_second or self.stats.current_rate_per_second
            )

        def reset_profile(self):
            self.stats.current_fraud_ratio = 0.18
            self.stats.current_rate_per_second = 3.0

        def export_dataset(self, output_path, events):
            return output_path

    monkeypatch.setattr(producer_main, "ProducerRuntime", FakeRuntime)
    app = producer_main.build_app()

    with TestClient(app) as client:
        status_response = client.get("/producer/status")
        burst_response = client.post(
            "/producer/burst",
            json={"scenario": "card_testing", "count": 4},
        )
        boost_response = client.post(
            "/producer/boost",
            json={"fraud_ratio": 0.7, "rate_per_second": 7.0, "duration_seconds": 30},
        )
        reset_response = client.post("/producer/reset")

        assert status_response.status_code == 200
        assert status_response.json()["current_rate_per_second"] == 6.0
        assert burst_response.status_code == 200
        assert burst_response.json()["count"] == 4
        assert boost_response.status_code == 200
        assert boost_response.json()["fraud_ratio"] == 0.7
        assert reset_response.status_code == 200
        assert reset_response.json()["rate_per_second"] == 3.0
