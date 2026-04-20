"""Shared Pydantic contracts for service communication."""

from fraud_platform_contracts.events import (
    AnalystFeedbackEvent,
    Channel,
    DeadLetterEvent,
    DecisionEvent,
    EnrichedTransactionEvent,
    FeatureVector,
    FeedbackLabel,
    FraudDecision,
    ModelMetadata,
    PaymentMethod,
    ReasonCode,
    RuleHit,
    ScoredTransactionEvent,
    Severity,
    SimulationScenario,
    TransactionEvent,
    ValidatedTransactionEvent,
)
from fraud_platform_contracts.health import DependencyStatus, HealthResponse
from fraud_platform_contracts.serde import dump_json, dump_json_str, load_json

__all__ = [
    "AnalystFeedbackEvent",
    "Channel",
    "DeadLetterEvent",
    "DecisionEvent",
    "DependencyStatus",
    "dump_json",
    "dump_json_str",
    "EnrichedTransactionEvent",
    "FeatureVector",
    "FeedbackLabel",
    "FraudDecision",
    "HealthResponse",
    "load_json",
    "ModelMetadata",
    "PaymentMethod",
    "ReasonCode",
    "RuleHit",
    "ScoredTransactionEvent",
    "Severity",
    "SimulationScenario",
    "TransactionEvent",
    "ValidatedTransactionEvent",
]
