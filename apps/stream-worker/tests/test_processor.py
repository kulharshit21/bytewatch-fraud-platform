from __future__ import annotations

from dataclasses import dataclass

from fraud_platform_common.config import RuntimeSettings
from fraud_platform_contracts import (
    FraudDecision,
    ModelMetadata,
    ReasonCode,
    RuleHit,
    Severity,
)
from fraud_platform_feature_store import MemoryFeatureStore
from fraud_platform_producer.generation import SyntheticTransactionGenerator
from fraud_platform_stream_worker.processor import FraudStreamProcessor


@dataclass
class FakeRepository:
    raw_saved: int = 0
    scored_saved: int = 0
    decision_saved: int = 0

    def save_raw_transaction(self, event, source_topic):
        self.raw_saved += 1
        return event.event_id

    def save_scored_transaction(self, scored, decision):
        self.scored_saved += 1
        return scored.event_id

    def save_decision(self, decision, scored_transaction_id):
        self.decision_saved += 1
        return decision.case_id


class FakeRuleEngine:
    def evaluate(self, event, features):
        return [
            RuleHit(
                rule_id="very_high_velocity",
                severity=Severity.HIGH,
                explanation="Velocity threshold crossed",
                score_delta=0.2,
            )
        ]


class FakeModelRuntime:
    def score(self, features, rule_hits):
        return (
            0.91,
            0.94,
            FraudDecision.BLOCK,
            ModelMetadata(
                model_name="fraud_xgboost",
                model_version="7",
                model_alias="champion",
                review_threshold=0.55,
                block_threshold=0.82,
            ),
            [ReasonCode(code="velocity_spike", description="Velocity elevated")],
        )


def test_processor_builds_and_persists_bundle():
    generator = SyntheticTransactionGenerator(seed=7, fraud_ratio=0.4)
    event = generator.generate()
    repository = FakeRepository()
    processor = FraudStreamProcessor(
        RuntimeSettings(service_name="stream-worker"),
        feature_store=MemoryFeatureStore(),
        repository=repository,
        rule_engine=FakeRuleEngine(),
        model_runtime=FakeModelRuntime(),
    )

    bundle = processor.process_event(event, source_topic="tx.raw")
    processor.persist_bundle(bundle, source_topic="tx.raw")

    assert bundle.decision.decision == FraudDecision.BLOCK
    assert bundle.scored.final_score == 0.94
    assert bundle.enriched.features.values["amount"] == event.amount
    assert repository.raw_saved == 1
    assert repository.scored_saved == 1
    assert repository.decision_saved == 1


def test_processor_routes_invalid_payload_to_dlq():
    processor = FraudStreamProcessor(
        RuntimeSettings(service_name="stream-worker"),
        feature_store=MemoryFeatureStore(),
        repository=FakeRepository(),
        rule_engine=FakeRuleEngine(),
        model_runtime=FakeModelRuntime(),
    )

    output = processor.process_payload({"amount": -5}, source_topic="tx.raw")

    assert len(output) == 1
    assert output[0].topic == "tx.dlq"
