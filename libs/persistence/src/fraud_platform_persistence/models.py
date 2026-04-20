import uuid
from datetime import datetime, timezone

from sqlalchemy import JSON, DateTime, Float, Index, Numeric, String, Text, Uuid
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from fraud_platform_persistence.base import Base

JsonType = JSON().with_variant(JSONB, "postgresql")


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        onupdate=utc_now,
        nullable=False,
    )


class RawTransaction(TimestampMixin, Base):
    __tablename__ = "transactions_raw"
    __table_args__ = (
        Index("ix_transactions_raw_event_time", "event_time"),
        Index("ix_transactions_raw_account_id", "account_id"),
        Index("ix_transactions_raw_merchant_id", "merchant_id"),
        {"postgresql_partition_by": "RANGE (event_time)"},
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    event_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    transaction_id: Mapped[str] = mapped_column(String(64), nullable=False)
    account_id: Mapped[str] = mapped_column(String(64), nullable=False)
    customer_id: Mapped[str] = mapped_column(String(64), nullable=False)
    merchant_id: Mapped[str] = mapped_column(String(64), nullable=False)
    amount: Mapped[float] = mapped_column(Numeric(14, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(8), nullable=False)
    channel: Mapped[str] = mapped_column(String(32), nullable=False)
    scenario: Mapped[str | None] = mapped_column(String(64))
    payload: Mapped[dict] = mapped_column(JsonType, nullable=False, default=dict)
    event_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    ingested_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)


class ScoredTransaction(TimestampMixin, Base):
    __tablename__ = "transactions_scored"
    __table_args__ = (
        Index("ix_transactions_scored_event_time", "event_time"),
        Index("ix_transactions_scored_decision", "decision"),
        Index("ix_transactions_scored_model_version", "model_version"),
        {"postgresql_partition_by": "RANGE (event_time)"},
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    event_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    transaction_id: Mapped[str] = mapped_column(String(64), nullable=False)
    account_id: Mapped[str] = mapped_column(String(64), nullable=False)
    merchant_id: Mapped[str] = mapped_column(String(64), nullable=False)
    model_name: Mapped[str] = mapped_column(String(128), nullable=False)
    model_version: Mapped[str] = mapped_column(String(128), nullable=False)
    decision: Mapped[str] = mapped_column(String(32), nullable=False)
    scenario: Mapped[str | None] = mapped_column(String(64))
    score: Mapped[float] = mapped_column(Float, nullable=False)
    threshold: Mapped[float] = mapped_column(Float, nullable=False)
    rule_hits: Mapped[list[dict]] = mapped_column(JsonType, nullable=False, default=list)
    features: Mapped[dict] = mapped_column(JsonType, nullable=False, default=dict)
    reason_codes: Mapped[list[dict]] = mapped_column(JsonType, nullable=False, default=list)
    event_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class FraudDecision(TimestampMixin, Base):
    __tablename__ = "fraud_decisions"
    __table_args__ = (
        Index("ix_fraud_decisions_transaction_id", "transaction_id"),
        Index("ix_fraud_decisions_decision", "decision"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    transaction_id: Mapped[str] = mapped_column(String(64), nullable=False)
    scored_transaction_id: Mapped[uuid.UUID | None] = mapped_column(Uuid(as_uuid=True))
    decision: Mapped[str] = mapped_column(String(32), nullable=False)
    source: Mapped[str] = mapped_column(String(32), nullable=False, default="hybrid_engine")
    case_status: Mapped[str] = mapped_column(String(32), nullable=False, default="open")
    model_metadata: Mapped[dict] = mapped_column(JsonType, nullable=False, default=dict)
    rule_hits: Mapped[list[dict]] = mapped_column(JsonType, nullable=False, default=list)
    decision_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)


class AnalystFeedback(TimestampMixin, Base):
    __tablename__ = "analyst_feedback"
    __table_args__ = (
        Index("ix_analyst_feedback_case_id", "case_id"),
        Index("ix_analyst_feedback_feedback_label", "feedback_label"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    case_id: Mapped[str] = mapped_column(String(64), nullable=False)
    transaction_id: Mapped[str] = mapped_column(String(64), nullable=False)
    analyst_id: Mapped[str] = mapped_column(String(64), nullable=False)
    feedback_label: Mapped[str] = mapped_column(String(32), nullable=False)
    notes: Mapped[str | None] = mapped_column(Text)


class ModelRegistryCache(TimestampMixin, Base):
    __tablename__ = "model_registry_cache"
    __table_args__ = (
        Index("ix_model_registry_cache_alias", "alias"),
        Index("ix_model_registry_cache_model_version", "model_version"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    model_name: Mapped[str] = mapped_column(String(128), nullable=False)
    model_version: Mapped[str] = mapped_column(String(128), nullable=False)
    alias: Mapped[str | None] = mapped_column(String(64))
    run_id: Mapped[str | None] = mapped_column(String(64))
    stage: Mapped[str | None] = mapped_column(String(64))
    metadata_json: Mapped[dict] = mapped_column("metadata", JsonType, nullable=False, default=dict)


class AuditLog(TimestampMixin, Base):
    __tablename__ = "audit_logs"
    __table_args__ = (
        Index("ix_audit_logs_entity_type", "entity_type"),
        Index("ix_audit_logs_entity_id", "entity_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    entity_type: Mapped[str] = mapped_column(String(64), nullable=False)
    entity_id: Mapped[str] = mapped_column(String(128), nullable=False)
    action: Mapped[str] = mapped_column(String(64), nullable=False)
    actor: Mapped[str] = mapped_column(String(64), nullable=False)
    payload: Mapped[dict] = mapped_column(JsonType, nullable=False, default=dict)
