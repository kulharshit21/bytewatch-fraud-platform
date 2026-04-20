from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID, uuid4

from fastapi.testclient import TestClient

from fraud_platform_contracts import (
    DecisionEvent,
    EnrichedTransactionEvent,
    FeatureVector,
    FeedbackLabel,
    FraudDecision,
    ModelMetadata,
    ReasonCode,
    RuleHit,
    ScoredTransactionEvent,
    Severity,
    ValidatedTransactionEvent,
)
from fraud_platform_producer.generation import SyntheticTransactionGenerator


class FakeKafkaProducer:
    def __init__(self, *args, **kwargs):
        self.messages = []

    def send(self, topic, key, value):
        self.messages.append((topic, key, value))

    def flush(self, timeout=None):
        return None

    def close(self, timeout=None):
        return None


@dataclass
class FakeFeatureStore:
    claimed: set[str]

    def claim_event(self, event_id: str) -> bool:
        if event_id in self.claimed:
            return False
        self.claimed.add(event_id)
        return True


class FakeRepository:
    def __init__(self, *args, **kwargs):
        self.feedback = []
        self.case_id = str(uuid4())
        self.transaction_id = "txn_case_001"
        self.event_id = str(uuid4())

    def get_transaction(self, transaction_id):
        return {"raw": {"transaction_id": transaction_id}, "scored": {"score": 0.92, "decision": "BLOCK"}}

    def list_cases(self, **kwargs):
        return {
            "items": [
                {
                    "case_id": self.case_id,
                    "transaction_id": self.transaction_id,
                    "decision": "BLOCK",
                    "status": "open",
                    "decision_time": "2026-04-20T00:00:00+00:00",
                    "score": 0.92,
                    "scenario": "account_takeover",
                    "amount": 4200.0,
                    "country": "AE",
                    "channel": "transfer",
                    "account_id": "acct_001",
                }
            ],
            "pagination": {"page": 1, "page_size": 20, "total": 1, "total_pages": 1},
        }

    def get_case(self, case_id):
        if case_id != self.case_id:
            return None
        return {
            "case_id": self.case_id,
            "decision": "BLOCK",
            "status": "open",
            "transaction_id": self.transaction_id,
            "model_metadata": {
                "model_name": "fraud_xgboost",
                "model_version": "3",
                "model_alias": "champion",
                "review_threshold": 0.55,
                "block_threshold": 0.82,
            },
            "rule_hits": [{"rule_id": "velocity", "explanation": "Velocity spike", "severity": "high"}],
            "raw_transaction": {"event_id": self.event_id, "transaction_id": self.transaction_id},
            "score": 0.92,
            "reason_codes": [{"code": "velocity_spike", "description": "Velocity elevated"}],
            "features": {"tx_count_5m": 7.0},
            "feedback": self.feedback,
            "timeline": [{"type": "scored", "timestamp": "2026-04-20T00:00:00+00:00", "detail": "Scored"}],
        }

    def add_feedback(self, feedback):
        self.feedback.append(
            {
                "feedback_id": str(feedback.feedback_id),
                "analyst_id": feedback.analyst_id,
                "feedback_label": feedback.feedback_label,
                "notes": feedback.notes,
                "created_at": feedback.created_at.isoformat(),
            }
        )

    def dashboard_overview(self, hours=24):
        return {
            "total_transactions": 12,
            "blocked_transactions": 4,
            "review_transactions": 3,
            "approved_transactions": 5,
            "average_score": 0.63,
            "last_updated_at": "2026-04-20T00:00:00+00:00",
        }

    def analytics_trends(self, hours=24):
        return [{"bucket": "2026-04-20T00:00:00+00:00", "decision": "BLOCK", "count": 4}]

    def cache_model_metadata(self, metadata):
        return None


class FakeTrainer:
    def __init__(self, *args, **kwargs):
        pass

    def get_current_metadata(self):
        return ModelMetadata(
            model_name="fraud_xgboost",
            model_version="3",
            model_alias="champion",
            review_threshold=0.55,
            block_threshold=0.82,
            metrics={"precision": 0.82},
        )


class FakeProcessor:
    def __init__(self, *args, **kwargs):
        self.feature_store = FakeFeatureStore(set())
        self.repository = FakeRepository()
        self.model_runtime = type("Loaded", (), {"reload": lambda self: type("Model", (), {"metadata": FakeTrainer().get_current_metadata()})()})()

    def process_event(self, event, source_topic):
        validated = ValidatedTransactionEvent(
            **event.model_dump(mode="python"),
            normalized_amount=event.amount,
            normalized_currency=event.currency,
            received_topic=source_topic,
        )
        enriched = EnrichedTransactionEvent(
            **validated.model_dump(mode="python"),
            features=FeatureVector(values={"amount": event.amount}),
            enrichment_latency_ms=1.5,
        )
        metadata = FakeTrainer().get_current_metadata()
        scored_payload = enriched.model_dump(mode="python")
        scored_payload["processing_stage"] = "scored"
        scored = ScoredTransactionEvent(
            **scored_payload,
            model_probability=0.91,
            final_score=0.95,
            model_metadata=metadata,
            rule_hits=[
                RuleHit(
                    rule_id="velocity",
                    severity=Severity.HIGH,
                    explanation="Velocity spike",
                    score_delta=0.2,
                )
            ],
            reason_codes=[ReasonCode(code="velocity_spike", description="Velocity elevated")],
            scoring_latency_ms=2.0,
        )
        decision = DecisionEvent(
            event_id=scored.event_id,
            transaction_id=scored.transaction_id,
            account_id=scored.account_id,
            decision=FraudDecision.BLOCK,
            final_score=scored.final_score,
            model_probability=scored.model_probability,
            model_metadata=metadata,
            rule_hits=scored.rule_hits,
            reason_codes=scored.reason_codes,
            simulation_scenario=scored.simulation_scenario,
        )
        return type("Bundle", (), {"validated": validated, "enriched": enriched, "scored": scored, "decision": decision})()

    def persist_bundle(self, bundle, source_topic):
        return None


def test_cases_and_predict_endpoints(monkeypatch):
    import fraud_platform_api.main as api_main

    monkeypatch.setattr(api_main, "KafkaProducer", FakeKafkaProducer)
    monkeypatch.setattr(api_main, "FraudRepository", FakeRepository)
    monkeypatch.setattr(api_main, "FraudStreamProcessor", FakeProcessor)
    monkeypatch.setattr(api_main, "FraudTrainer", FakeTrainer)

    app = api_main.build_app()

    with TestClient(app) as client:
        generator = SyntheticTransactionGenerator(seed=5)
        event = generator.generate().model_dump(mode="json")

        predict_response = client.post("/predict", json=event)
        cases_response = client.get("/cases")

        assert predict_response.status_code == 200
        assert predict_response.json()["decision"]["decision"] == "BLOCK"
        assert cases_response.status_code == 200
        assert cases_response.json()["items"][0]["decision"] == "BLOCK"


def test_feedback_endpoint_records_feedback(monkeypatch):
    import fraud_platform_api.main as api_main

    monkeypatch.setattr(api_main, "KafkaProducer", FakeKafkaProducer)
    monkeypatch.setattr(api_main, "FraudRepository", FakeRepository)
    monkeypatch.setattr(api_main, "FraudStreamProcessor", FakeProcessor)
    monkeypatch.setattr(api_main, "FraudTrainer", FakeTrainer)

    app = api_main.build_app()

    with TestClient(app) as client:
        repository: FakeRepository = app.state.repository
        producer: FakeKafkaProducer = app.state.kafka_producer
        case_id = client.get("/cases").json()["items"][0]["case_id"]

        response = client.post(
            f"/cases/{case_id}/feedback",
            json={
                "analyst_id": "analyst_01",
                "feedback_label": FeedbackLabel.FRAUD,
                "notes": "Confirmed fraud pattern",
            },
        )
        case_response = client.get(f"/cases/{case_id}")

        assert response.status_code == 200
        assert repository.feedback[0]["feedback_label"] == "fraud"
        assert producer.messages[0][0] == app.state.settings.kafka_feedback_topic
        assert producer.messages[0][1] == case_id
        assert case_response.status_code == 200
        assert case_response.json()["feedback"][0]["feedback_label"] == "fraud"


def test_grafana_alert_webhook_accepts_local_notifications(monkeypatch):
    import fraud_platform_api.main as api_main

    monkeypatch.setattr(api_main, "KafkaProducer", FakeKafkaProducer)
    monkeypatch.setattr(api_main, "FraudRepository", FakeRepository)
    monkeypatch.setattr(api_main, "FraudStreamProcessor", FakeProcessor)
    monkeypatch.setattr(api_main, "FraudTrainer", FakeTrainer)

    app = api_main.build_app()

    with TestClient(app) as client:
        response = client.post(
            "/ops/grafana-alerts",
            json={
                "alerts": [
                    {"status": "firing", "labels": {"alertname": "drift-threshold"}},
                    {"status": "resolved", "labels": {"alertname": "api-error-rate"}},
                ]
            },
        )

        assert response.status_code == 200
        assert response.json() == {
            "status": "accepted",
            "alert_count": 2,
            "statuses": ["firing", "resolved"],
        }
