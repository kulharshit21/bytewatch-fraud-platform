from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum
from typing import Any, Literal
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field


def utc_now() -> datetime:
    return datetime.now(UTC)


class FraudBaseModel(BaseModel):
    model_config = ConfigDict(
        populate_by_name=True,
        use_enum_values=True,
        extra="forbid",
        json_encoders={datetime: lambda value: value.isoformat()},
    )


class FraudDecision(StrEnum):
    APPROVE = "APPROVE"
    REVIEW = "REVIEW"
    BLOCK = "BLOCK"


class FeedbackLabel(StrEnum):
    FRAUD = "fraud"
    FALSE_POSITIVE = "false_positive"
    LEGITIMATE = "legitimate"
    REVIEW = "review"


class Severity(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class Channel(StrEnum):
    POS = "pos"
    ECOMMERCE = "ecommerce"
    UPI = "upi"
    WALLET = "wallet"
    TRANSFER = "transfer"


class PaymentMethod(StrEnum):
    CREDIT_CARD = "credit_card"
    DEBIT_CARD = "debit_card"
    UPI = "upi"
    WALLET = "wallet"
    BANK_TRANSFER = "bank_transfer"


class SimulationScenario(StrEnum):
    NORMAL_BEHAVIOR = "normal_behavior"
    VELOCITY_BURST = "velocity_burst_fraud"
    IMPOSSIBLE_TRAVEL = "impossible_travel"
    CARD_TESTING = "card_testing"
    ACCOUNT_TAKEOVER = "account_takeover"
    NEW_DEVICE_HIGH_AMOUNT = "new_device_high_amount"
    RISKY_MERCHANT = "risky_merchant_pattern"


class RuleHit(FraudBaseModel):
    rule_id: str
    severity: Severity
    score_delta: float = 0.0
    explanation: str
    metadata: dict[str, Any] = Field(default_factory=dict)


class ReasonCode(FraudBaseModel):
    code: str
    description: str
    value: str | float | int | bool | None = None


class ModelMetadata(FraudBaseModel):
    model_name: str
    model_version: str
    model_alias: str
    registered_at: datetime | None = None
    review_threshold: float
    block_threshold: float
    run_id: str | None = None
    metrics: dict[str, float] = Field(default_factory=dict)


class FeatureVector(FraudBaseModel):
    values: dict[str, float | int | bool | str]


class TransactionEvent(FraudBaseModel):
    event_id: UUID = Field(default_factory=uuid4)
    event_time: datetime = Field(default_factory=utc_now)
    account_id: str
    customer_id: str
    transaction_id: str
    payment_instrument_id: str
    merchant_id: str
    merchant_category: str
    amount: float
    currency: str
    country: str
    city: str
    latitude: float
    longitude: float
    channel: Channel
    device_id: str
    ip_address: str
    user_agent_hash: str
    email_hash: str
    phone_hash: str
    prior_auth_failures: int = 0
    payment_method: PaymentMethod
    card_present: bool
    is_international: bool
    label: int | None = Field(default=None, description="Synthetic label only.")
    simulation_scenario: SimulationScenario
    metadata: dict[str, Any] = Field(default_factory=dict)


class ValidatedTransactionEvent(TransactionEvent):
    normalized_amount: float
    normalized_currency: str
    validation_status: Literal["valid"] = "valid"
    validation_errors: list[str] = Field(default_factory=list)
    received_topic: str = "tx.raw"


class EnrichedTransactionEvent(ValidatedTransactionEvent):
    features: FeatureVector
    enrichment_latency_ms: float
    processing_stage: Literal["enriched"] = "enriched"


class ScoredTransactionEvent(EnrichedTransactionEvent):
    model_probability: float
    final_score: float
    model_metadata: ModelMetadata
    rule_hits: list[RuleHit] = Field(default_factory=list)
    reason_codes: list[ReasonCode] = Field(default_factory=list)
    scoring_latency_ms: float
    processing_stage: Literal["scored"] = "scored"


class DecisionEvent(FraudBaseModel):
    case_id: UUID = Field(default_factory=uuid4)
    event_id: UUID
    transaction_id: str
    account_id: str
    decision: FraudDecision
    status: str = "open"
    final_score: float
    model_probability: float
    model_metadata: ModelMetadata
    rule_hits: list[RuleHit] = Field(default_factory=list)
    reason_codes: list[ReasonCode] = Field(default_factory=list)
    decided_at: datetime = Field(default_factory=utc_now)
    simulation_scenario: SimulationScenario


class AnalystFeedbackEvent(FraudBaseModel):
    feedback_id: UUID = Field(default_factory=uuid4)
    case_id: UUID
    transaction_id: str
    event_id: UUID
    analyst_id: str
    feedback_label: FeedbackLabel
    notes: str | None = None
    created_at: datetime = Field(default_factory=utc_now)


class DeadLetterEvent(FraudBaseModel):
    dead_letter_id: UUID = Field(default_factory=uuid4)
    event_id: UUID | None = None
    source_topic: str
    failed_stage: str
    error_message: str
    raw_payload: dict[str, Any] | None = None
    created_at: datetime = Field(default_factory=utc_now)
