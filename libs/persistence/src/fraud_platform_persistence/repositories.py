from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from math import ceil
from typing import Any
from uuid import UUID

from sqlalchemy import desc, func, select
from sqlalchemy.orm import Session, sessionmaker

from fraud_platform_common.config import RuntimeSettings
from fraud_platform_contracts import (
    AnalystFeedbackEvent,
    DecisionEvent,
    ModelMetadata,
    ScoredTransactionEvent,
    TransactionEvent,
)
from fraud_platform_persistence.db import build_session_factory
from fraud_platform_persistence.models import (
    AnalystFeedback,
    AuditLog,
    FraudDecision,
    ModelRegistryCache,
    RawTransaction,
    ScoredTransaction,
)


@dataclass(slots=True)
class Pagination:
    page: int
    page_size: int
    total: int

    @property
    def total_pages(self) -> int:
        return max(1, ceil(self.total / self.page_size))


class FraudRepository:
    def __init__(self, settings: RuntimeSettings) -> None:
        self._session_factory: sessionmaker[Session] = build_session_factory(settings)

    def _session(self) -> Session:
        return self._session_factory()

    def save_raw_transaction(self, event: TransactionEvent, source_topic: str) -> UUID:
        with self._session() as session:
            row = RawTransaction(
                event_id=event.event_id,
                transaction_id=event.transaction_id,
                account_id=event.account_id,
                customer_id=event.customer_id,
                merchant_id=event.merchant_id,
                amount=event.amount,
                currency=event.currency,
                channel=event.channel,
                scenario=event.simulation_scenario,
                payload={
                    **event.model_dump(mode="json"),
                    "source_topic": source_topic,
                },
                event_time=event.event_time,
            )
            session.add(row)
            session.commit()
            return row.id

    def save_scored_transaction(self, scored: ScoredTransactionEvent, decision: str) -> UUID:
        with self._session() as session:
            row = ScoredTransaction(
                event_id=scored.event_id,
                transaction_id=scored.transaction_id,
                account_id=scored.account_id,
                merchant_id=scored.merchant_id,
                model_name=scored.model_metadata.model_name,
                model_version=scored.model_metadata.model_version,
                decision=decision,
                scenario=scored.simulation_scenario,
                score=scored.final_score,
                threshold=scored.model_metadata.review_threshold,
                rule_hits=[rule.model_dump(mode="json") for rule in scored.rule_hits],
                features=scored.features.values,
                reason_codes=[reason.model_dump(mode="json") for reason in scored.reason_codes],
                event_time=scored.event_time,
            )
            session.add(row)
            session.commit()
            return row.id

    def save_decision(self, decision: DecisionEvent, scored_transaction_id: UUID | None) -> UUID:
        with self._session() as session:
            row = FraudDecision(
                id=decision.case_id,
                transaction_id=decision.transaction_id,
                scored_transaction_id=scored_transaction_id,
                decision=decision.decision,
                source="stream_worker",
                case_status=decision.status,
                model_metadata=decision.model_metadata.model_dump(mode="json"),
                rule_hits=[rule.model_dump(mode="json") for rule in decision.rule_hits],
                decision_time=decision.decided_at,
            )
            session.add(row)
            session.commit()
            return row.id

    def add_feedback(self, feedback: AnalystFeedbackEvent) -> UUID:
        with self._session() as session:
            fraud_case = session.get(FraudDecision, feedback.case_id)
            if fraud_case is not None:
                fraud_case.case_status = "closed" if feedback.feedback_label != "review" else "open"
            row = AnalystFeedback(
                id=feedback.feedback_id,
                case_id=str(feedback.case_id),
                transaction_id=feedback.transaction_id,
                analyst_id=feedback.analyst_id,
                feedback_label=feedback.feedback_label,
                notes=feedback.notes,
            )
            session.add(row)
            session.add(
                AuditLog(
                    entity_type="fraud_case",
                    entity_id=str(feedback.case_id),
                    action="analyst_feedback",
                    actor=feedback.analyst_id,
                    payload=feedback.model_dump(mode="json"),
                )
            )
            session.commit()
            return row.id

    def cache_model_metadata(self, metadata: ModelMetadata) -> None:
        with self._session() as session:
            session.add(
                ModelRegistryCache(
                    model_name=metadata.model_name,
                    model_version=metadata.model_version,
                    alias=metadata.model_alias,
                    run_id=metadata.run_id,
                    stage="active",
                    metadata_json=metadata.model_dump(mode="json"),
                )
            )
            session.commit()

    def get_current_model(self, alias: str = "champion") -> dict[str, Any] | None:
        with self._session() as session:
            query = (
                select(ModelRegistryCache)
                .where(ModelRegistryCache.alias == alias)
                .order_by(desc(ModelRegistryCache.created_at))
            )
            row = session.execute(query).scalars().first()
            return row.metadata_json if row else None

    def get_transaction(self, transaction_id: str) -> dict[str, Any] | None:
        with self._session() as session:
            raw = (
                session.execute(
                    select(RawTransaction)
                    .where(RawTransaction.transaction_id == transaction_id)
                    .order_by(desc(RawTransaction.event_time))
                )
                .scalars()
                .first()
            )
            scored = (
                session.execute(
                    select(ScoredTransaction)
                    .where(ScoredTransaction.transaction_id == transaction_id)
                    .order_by(desc(ScoredTransaction.event_time))
                )
                .scalars()
                .first()
            )
            if raw is None:
                return None
            return {
                "raw": raw.payload,
                "scored": None
                if scored is None
                else {
                    "score": scored.score,
                    "decision": scored.decision,
                    "model_name": scored.model_name,
                    "model_version": scored.model_version,
                    "rule_hits": scored.rule_hits,
                    "reason_codes": scored.reason_codes,
                    "features": scored.features,
                },
            }

    def list_cases(
        self,
        *,
        page: int = 1,
        page_size: int = 20,
        status: str | None = None,
        decision: str | None = None,
        search: str | None = None,
        sort_by: str = "decision_time",
        sort_order: str = "desc",
    ) -> dict[str, Any]:
        with self._session() as session:
            order_column = FraudDecision.decision_time
            if sort_by == "decision":
                order_column = FraudDecision.decision
            query = select(FraudDecision)
            if status:
                query = query.where(FraudDecision.case_status == status)
            if decision:
                query = query.where(FraudDecision.decision == decision)
            if search:
                query = query.where(FraudDecision.transaction_id.contains(search))

            query = query.order_by(order_column if sort_order == "asc" else desc(order_column))

            total = session.execute(select(func.count()).select_from(query.subquery())).scalar_one()
            rows = (
                session.execute(query.offset((page - 1) * page_size).limit(page_size))
                .scalars()
                .all()
            )
            items = []
            for row in rows:
                scored = (
                    session.execute(
                        select(ScoredTransaction)
                        .where(ScoredTransaction.transaction_id == row.transaction_id)
                        .order_by(desc(ScoredTransaction.event_time))
                    )
                    .scalars()
                    .first()
                )
                raw = (
                    session.execute(
                        select(RawTransaction)
                        .where(RawTransaction.transaction_id == row.transaction_id)
                        .order_by(desc(RawTransaction.event_time))
                    )
                    .scalars()
                    .first()
                )
                items.append(
                    {
                        "case_id": str(row.id),
                        "transaction_id": row.transaction_id,
                        "decision": row.decision,
                        "status": row.case_status,
                        "decision_time": row.decision_time.isoformat(),
                        "score": scored.score if scored else None,
                        "scenario": scored.scenario if scored else None,
                        "rule_hits": scored.rule_hits if scored else [],
                        "account_id": scored.account_id if scored else None,
                        "merchant_id": scored.merchant_id if scored else None,
                        "amount": None if raw is None else float(raw.amount),
                        "country": None if raw is None else raw.payload.get("country"),
                        "channel": None if raw is None else raw.payload.get("channel"),
                    }
                )
            pagination = Pagination(page=page, page_size=page_size, total=int(total))
            return {
                "items": items,
                "pagination": {
                    "page": pagination.page,
                    "page_size": pagination.page_size,
                    "total": pagination.total,
                    "total_pages": pagination.total_pages,
                },
            }

    def get_case(self, case_id: str) -> dict[str, Any] | None:
        with self._session() as session:
            decision = session.get(FraudDecision, UUID(case_id))
            if decision is None:
                return None
            scored = (
                session.execute(
                    select(ScoredTransaction)
                    .where(ScoredTransaction.transaction_id == decision.transaction_id)
                    .order_by(desc(ScoredTransaction.event_time))
                )
                .scalars()
                .first()
            )
            raw = (
                session.execute(
                    select(RawTransaction)
                    .where(RawTransaction.transaction_id == decision.transaction_id)
                    .order_by(desc(RawTransaction.event_time))
                )
                .scalars()
                .first()
            )
            feedback = (
                session.execute(
                    select(AnalystFeedback)
                    .where(AnalystFeedback.case_id == case_id)
                    .order_by(desc(AnalystFeedback.created_at))
                )
                .scalars()
                .all()
            )
            timeline = [
                {
                    "type": "ingested",
                    "timestamp": raw.event_time.isoformat(),
                    "detail": "Transaction received",
                }
                for raw in ([raw] if raw else [])
            ]
            if scored:
                timeline.append(
                    {
                        "type": "scored",
                        "timestamp": scored.event_time.isoformat(),
                        "detail": f"Scored {scored.score:.3f} with {scored.model_name} {scored.model_version}",
                    }
                )
            timeline.extend(
                {
                    "type": "feedback",
                    "timestamp": item.created_at.isoformat(),
                    "detail": f"{item.analyst_id} marked {item.feedback_label}",
                }
                for item in feedback
            )
            payload = raw.payload if raw else {}
            return {
                "case_id": case_id,
                "decision": decision.decision,
                "status": decision.case_status,
                "transaction_id": decision.transaction_id,
                "model_metadata": decision.model_metadata,
                "rule_hits": decision.rule_hits,
                "raw_transaction": payload,
                "score": scored.score if scored else None,
                "reason_codes": scored.reason_codes if scored else [],
                "features": scored.features if scored else {},
                "feedback": [
                    {
                        "feedback_id": str(item.id),
                        "analyst_id": item.analyst_id,
                        "feedback_label": item.feedback_label,
                        "notes": item.notes,
                        "created_at": item.created_at.isoformat(),
                    }
                    for item in feedback
                ],
                "timeline": sorted(timeline, key=lambda item: item["timestamp"]),
            }

    def dashboard_overview(self, hours: int = 24) -> dict[str, Any]:
        with self._session() as session:
            since = datetime.now(UTC) - timedelta(hours=hours)
            base_query = select(ScoredTransaction).where(ScoredTransaction.event_time >= since)
            total = session.execute(select(func.count()).select_from(base_query.subquery())).scalar_one()
            block = session.execute(
                select(func.count()).select_from(base_query.where(ScoredTransaction.decision == "BLOCK").subquery())
            ).scalar_one()
            review = session.execute(
                select(func.count()).select_from(base_query.where(ScoredTransaction.decision == "REVIEW").subquery())
            ).scalar_one()
            avg_score = session.execute(
                select(func.avg(ScoredTransaction.score)).where(ScoredTransaction.event_time >= since)
            ).scalar_one()
            return {
                "window_hours": hours,
                "total_transactions": int(total),
                "blocked_transactions": int(block),
                "review_transactions": int(review),
                "approved_transactions": int(total - block - review),
                "average_score": float(avg_score or 0.0),
                "last_updated_at": datetime.now(UTC).isoformat(),
            }

    def analytics_trends(self, hours: int = 24) -> list[dict[str, Any]]:
        with self._session() as session:
            since = datetime.now(UTC) - timedelta(hours=hours)
            rows = session.execute(
                select(
                    func.date_trunc("hour", ScoredTransaction.event_time).label("bucket"),
                    ScoredTransaction.decision,
                    func.count().label("count"),
                )
                .where(ScoredTransaction.event_time >= since)
                .group_by("bucket", ScoredTransaction.decision)
                .order_by("bucket")
            ).all()
            return [
                {
                    "bucket": row.bucket.isoformat(),
                    "decision": row.decision,
                    "count": int(row.count),
                }
                for row in rows
            ]

    def training_frame(self) -> list[dict[str, Any]]:
        with self._session() as session:
            rows = (
                session.execute(select(RawTransaction).order_by(RawTransaction.event_time.asc()))
                .scalars()
                .all()
            )
            feedback_rows = session.execute(select(AnalystFeedback)).scalars().all()
            feedback_by_transaction: dict[str, list[AnalystFeedback]] = defaultdict(list)
            for feedback in feedback_rows:
                feedback_by_transaction[feedback.transaction_id].append(feedback)

            items: list[dict[str, Any]] = []
            for row in rows:
                payload = dict(row.payload)
                transaction_feedback = feedback_by_transaction.get(row.transaction_id, [])
                if transaction_feedback:
                    transaction_feedback = sorted(
                        transaction_feedback,
                        key=lambda item: item.created_at,
                        reverse=True,
                    )
                    labels = [item.feedback_label for item in transaction_feedback]
                    latest = transaction_feedback[0]
                    payload["latest_feedback_label"] = latest.feedback_label
                    payload["feedback_labels"] = labels
                    payload["feedback_count"] = len(labels)
                    feedback_label = self._feedback_label_to_training_label(latest.feedback_label)
                    if feedback_label is not None:
                        payload["label"] = feedback_label
                        payload["label_source"] = "analyst_feedback"
                    else:
                        payload["label_source"] = "synthetic"
                else:
                    payload["feedback_count"] = 0
                    payload["feedback_labels"] = []
                    payload["latest_feedback_label"] = None
                    payload["label_source"] = "synthetic" if payload.get("label") is not None else "unlabeled"
                items.append(payload)
            return items

    @staticmethod
    def _feedback_label_to_training_label(feedback_label: str) -> int | None:
        if feedback_label == "fraud":
            return 1
        if feedback_label in {"false_positive", "legitimate"}:
            return 0
        return None
