from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any
from uuid import UUID

from bytewax.connectors.kafka import KafkaSinkMessage

from fraud_platform_common.config import RuntimeSettings
from fraud_platform_contracts import (
    DeadLetterEvent,
    DecisionEvent,
    EnrichedTransactionEvent,
    FeatureVector,
    ScoredTransactionEvent,
    TransactionEvent,
    ValidatedTransactionEvent,
    dump_json,
    load_json,
)
from fraud_platform_feature_engineering import compute_feature_values
from fraud_platform_feature_store import RedisFeatureStore
from fraud_platform_model_runtime import ModelRuntime
from fraud_platform_observability.metrics import DLQ_COUNTER, WORKER_EVENTS_COUNTER, WORKER_LATENCY_SECONDS
from fraud_platform_persistence import FraudRepository
from fraud_platform_rules import RuleEngine


@dataclass(slots=True)
class ProcessedBundle:
    validated: ValidatedTransactionEvent
    enriched: EnrichedTransactionEvent
    scored: ScoredTransactionEvent
    decision: DecisionEvent


class FraudStreamProcessor:
    def __init__(
        self,
        settings: RuntimeSettings,
        *,
        feature_store: Any | None = None,
        repository: FraudRepository | None = None,
        rule_engine: RuleEngine | None = None,
        model_runtime: ModelRuntime | None = None,
    ) -> None:
        self.settings = settings
        self.feature_store = feature_store or RedisFeatureStore(settings)
        self.repository = repository or FraudRepository(settings)
        self.rule_engine = rule_engine or RuleEngine.from_yaml(settings.rules_config_path)
        self.model_runtime = model_runtime or ModelRuntime(settings)

    def normalize(self, event: TransactionEvent, source_topic: str) -> ValidatedTransactionEvent:
        errors: list[str] = []
        if not event.account_id:
            errors.append("account_id is required")
        if not event.transaction_id:
            errors.append("transaction_id is required")
        if event.amount <= 0:
            errors.append("amount must be positive")
        if event.prior_auth_failures < 0:
            errors.append("prior_auth_failures cannot be negative")
        if errors:
            raise ValueError(", ".join(errors))

        return ValidatedTransactionEvent(
            **event.model_dump(mode="python"),
            normalized_amount=round(float(event.amount), 2),
            normalized_currency=event.currency.upper(),
            validation_errors=[],
            received_topic=source_topic,
        )

    def _dlq_message(
        self,
        *,
        failed_stage: str,
        error_message: str,
        raw_payload: dict[str, Any] | None,
        event_id: UUID | None,
    ) -> KafkaSinkMessage[str | None, bytes]:
        dead_letter = DeadLetterEvent(
            event_id=event_id,
            source_topic=self.settings.kafka_raw_topic,
            failed_stage=failed_stage,
            error_message=error_message,
            raw_payload=raw_payload,
        )
        DLQ_COUNTER.labels(failed_stage=failed_stage).inc()
        return KafkaSinkMessage(
            key=None if event_id is None else str(event_id),
            value=dump_json(dead_letter),
            topic=self.settings.kafka_dlq_topic,
        )

    def process_event(self, event: TransactionEvent, *, source_topic: str) -> ProcessedBundle:
        validated = self.normalize(event, source_topic)
        enrichment_started = time.perf_counter()
        context = self.feature_store.get_context(validated)
        feature_values = compute_feature_values(validated, context)
        enriched = EnrichedTransactionEvent(
            **validated.model_dump(mode="python"),
            features=FeatureVector(values=feature_values),
            enrichment_latency_ms=(time.perf_counter() - enrichment_started) * 1000,
        )

        scoring_started = time.perf_counter()
        rule_hits = self.rule_engine.evaluate(validated, feature_values)
        (
            model_probability,
            final_score,
            decision_label,
            model_metadata,
            reason_codes,
        ) = self.model_runtime.score(feature_values, rule_hits)
        scored = ScoredTransactionEvent(
            **enriched.model_dump(mode="python", exclude={"processing_stage"}),
            model_probability=model_probability,
            final_score=final_score,
            model_metadata=model_metadata,
            rule_hits=rule_hits,
            reason_codes=reason_codes,
            scoring_latency_ms=(time.perf_counter() - scoring_started) * 1000,
        )
        decision = DecisionEvent(
            event_id=scored.event_id,
            transaction_id=scored.transaction_id,
            account_id=scored.account_id,
            decision=decision_label,
            final_score=scored.final_score,
            model_probability=scored.model_probability,
            model_metadata=scored.model_metadata,
            rule_hits=scored.rule_hits,
            reason_codes=scored.reason_codes,
            simulation_scenario=scored.simulation_scenario,
        )
        return ProcessedBundle(
            validated=validated,
            enriched=enriched,
            scored=scored,
            decision=decision,
        )

    def persist_bundle(self, bundle: ProcessedBundle, *, source_topic: str) -> None:
        self.repository.save_raw_transaction(bundle.validated, source_topic)
        scored_id = self.repository.save_scored_transaction(bundle.scored, bundle.decision.decision)
        self.repository.save_decision(bundle.decision, scored_id)
        self.feature_store.update_state(bundle.validated)

    def process_payload(
        self,
        payload: bytes | str | dict[str, Any],
        *,
        source_topic: str,
    ) -> list[KafkaSinkMessage[str | None, bytes]]:
        started = time.perf_counter()
        try:
            event = load_json(TransactionEvent, payload)
        except Exception as exc:
            WORKER_EVENTS_COUNTER.labels(stage="validation", status="failed").inc()
            return [
                self._dlq_message(
                    failed_stage="validation",
                    error_message=str(exc),
                    raw_payload=self._coerce_raw_payload(payload),
                    event_id=None,
                )
            ]

        if not self.feature_store.claim_event(str(event.event_id)):
            WORKER_EVENTS_COUNTER.labels(stage="dedupe", status="duplicate").inc()
            return []

        try:
            bundle = self.process_event(event, source_topic=source_topic)
            self.persist_bundle(bundle, source_topic=source_topic)
            WORKER_EVENTS_COUNTER.labels(stage="validated", status="ok").inc()
            WORKER_EVENTS_COUNTER.labels(stage="enriched", status="ok").inc()
            WORKER_EVENTS_COUNTER.labels(stage="decisioned", status=bundle.decision.decision).inc()
            WORKER_LATENCY_SECONDS.labels(stage="end_to_end").observe(time.perf_counter() - started)
            return self._bundle_messages(bundle)
        except Exception as exc:
            WORKER_EVENTS_COUNTER.labels(stage="processing", status="failed").inc()
            return [
                self._dlq_message(
                    failed_stage="processing",
                    error_message=str(exc),
                    raw_payload=event.model_dump(mode="json"),
                    event_id=event.event_id,
                )
            ]

    def source_error_message(self, error: Any) -> KafkaSinkMessage[str | None, bytes]:
        return self._dlq_message(
            failed_stage="kafka_source",
            error_message=repr(error),
            raw_payload={"error": repr(error)},
            event_id=None,
        )

    def _bundle_messages(self, bundle: ProcessedBundle) -> list[KafkaSinkMessage[str, bytes]]:
        account_key = bundle.validated.account_id
        return [
            KafkaSinkMessage(
                key=account_key,
                value=dump_json(bundle.validated),
                topic=self.settings.kafka_validated_topic,
            ),
            KafkaSinkMessage(
                key=account_key,
                value=dump_json(bundle.enriched),
                topic=self.settings.kafka_enriched_topic,
            ),
            KafkaSinkMessage(
                key=account_key,
                value=dump_json(bundle.scored),
                topic=self.settings.kafka_scored_topic,
            ),
            KafkaSinkMessage(
                key=account_key,
                value=dump_json(bundle.decision),
                topic=self.settings.kafka_decisions_topic,
            ),
        ]

    @staticmethod
    def _coerce_raw_payload(payload: bytes | str | dict[str, Any]) -> dict[str, Any] | None:
        if isinstance(payload, dict):
            return payload
        if isinstance(payload, bytes):
            return {"payload": payload.decode("utf-8", errors="replace")}
        if isinstance(payload, str):
            return {"payload": payload}
        return None
