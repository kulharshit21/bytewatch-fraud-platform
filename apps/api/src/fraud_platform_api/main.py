from __future__ import annotations

import logging
import uuid

import httpx
import uvicorn
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fraud_platform_common.config import RuntimeSettings
from fraud_platform_common.service import (
    create_service_app,
    dependency_from_hostport,
    dependency_from_url,
)
from fraud_platform_contracts import AnalystFeedbackEvent, dump_json
from fraud_platform_persistence import FraudRepository
from fraud_platform_stream_worker.processor import FraudStreamProcessor
from fraud_platform_trainer.training import FraudTrainer
from kafka import KafkaProducer

from fraud_platform_api.schemas import (
    FeedbackRequest,
    PredictRequest,
    ProducerBoostRequest,
    ProducerBurstRequest,
)

logger = logging.getLogger(__name__)


class ApiSettings(RuntimeSettings):
    service_name: str = "api"
    host: str = "0.0.0.0"

    def __init__(self, **values: object) -> None:
        super().__init__(**values)
        self.port = self.api_port


async def _service_json_request(
    *,
    base_url: str,
    method: str,
    path: str,
    payload: dict[str, object] | None = None,
) -> dict[str, object]:
    url = f"{base_url.rstrip('/')}{path}"
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.request(method=method, url=url, json=payload)
            response.raise_for_status()
            return response.json()
    except httpx.HTTPStatusError as exc:
        detail = _http_error_detail(exc.response)
        raise HTTPException(status_code=exc.response.status_code, detail=detail) from exc
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=503, detail=f"Unable to reach {url}: {exc}") from exc


async def _optional_service_json_request(
    *,
    base_url: str,
    method: str,
    path: str,
) -> dict[str, object]:
    try:
        payload = await _service_json_request(base_url=base_url, method=method, path=path)
        return {"available": True, **payload}
    except HTTPException as exc:
        return {"available": False, "error": exc.detail}


def _http_error_detail(response: httpx.Response) -> str:
    try:
        payload = response.json()
    except ValueError:
        return f"Request failed with {response.status_code}"
    if isinstance(payload, dict) and payload.get("detail"):
        return str(payload["detail"])
    return f"Request failed with {response.status_code}"


def _startup(app: FastAPI) -> None:
    settings: ApiSettings = app.state.settings
    app.state.repository = FraudRepository(settings)
    app.state.processor = FraudStreamProcessor(settings)
    app.state.trainer = FraudTrainer(settings)
    app.state.kafka_producer = KafkaProducer(
        bootstrap_servers=settings.kafka_bootstrap_servers,
        value_serializer=lambda event: dump_json(event),
        key_serializer=lambda value: value.encode("utf-8"),
        linger_ms=50,
    )
    app.state.worker_ready = True


def _shutdown(app: FastAPI) -> None:
    producer: KafkaProducer | None = getattr(app.state, "kafka_producer", None)
    if producer is not None:
        producer.flush(timeout=5)
        producer.close(timeout=5)


def build_app() -> FastAPI:
    settings = ApiSettings()
    app = create_service_app(
        settings=settings,
        description="Fraud scoring API, case management API, and analytics service.",
        dependencies=[
            dependency_from_hostport("kafka", settings.kafka_bootstrap_servers, 9092),
            dependency_from_url("postgres", settings.database_url, 5432),
            dependency_from_url("redis", settings.redis_url, 6379),
            dependency_from_url("mlflow", settings.mlflow_tracking_uri, 5000, required=False),
        ],
        extra_metadata={
            "role": "predict, case review, analyst feedback, and dashboard analytics",
        },
        startup_callbacks=[_startup],
        shutdown_callbacks=[_shutdown],
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[
            "http://localhost:3001",
            "http://127.0.0.1:3001",
            settings.api_public_base_url.replace(":8000", ":3001"),
        ],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    api_routes(app)
    return app


def api_routes(app: FastAPI) -> None:
    @app.post("/predict", tags=["fraud"])
    async def predict(payload: PredictRequest) -> dict[str, object]:
        processor: FraudStreamProcessor = app.state.processor
        if not processor.feature_store.claim_event(str(payload.event_id)):
            raise HTTPException(status_code=409, detail="Duplicate event_id already processed.")
        bundle = processor.process_event(payload, source_topic="api.predict")
        processor.persist_bundle(bundle, source_topic="api.predict")
        return _bundle_to_response(bundle)

    @app.get("/transactions/{transaction_id}", tags=["transactions"])
    async def get_transaction(transaction_id: str) -> dict[str, object]:
        repository: FraudRepository = app.state.repository
        transaction = repository.get_transaction(transaction_id)
        if transaction is None:
            raise HTTPException(status_code=404, detail="Transaction not found.")
        return transaction

    @app.get("/cases", tags=["cases"])
    async def list_cases(
        page: int = Query(default=1, ge=1),
        page_size: int = Query(default=20, ge=1, le=100),
        status: str | None = None,
        decision: str | None = None,
        search: str | None = None,
        sort_by: str = Query(default="decision_time"),
        sort_order: str = Query(default="desc", pattern="^(asc|desc)$"),
    ) -> dict[str, object]:
        repository: FraudRepository = app.state.repository
        return repository.list_cases(
            page=page,
            page_size=page_size,
            status=status,
            decision=decision,
            search=search,
            sort_by=sort_by,
            sort_order=sort_order,
        )

    @app.get("/cases/live", tags=["cases"])
    async def live_cases(
        page: int = Query(default=1, ge=1),
        page_size: int = Query(default=20, ge=1, le=100),
        status: str | None = None,
        decision: str | None = None,
        search: str | None = None,
        sort_by: str = Query(default="decision_time"),
        sort_order: str = Query(default="desc", pattern="^(asc|desc)$"),
        recent_seconds: int = Query(default=30, ge=10, le=300),
        activity_limit: int = Query(default=6, ge=1, le=12),
    ) -> dict[str, object]:
        repository: FraudRepository = app.state.repository
        payload = repository.list_cases(
            page=page,
            page_size=page_size,
            status=status,
            decision=decision,
            search=search,
            sort_by=sort_by,
            sort_order=sort_order,
        )
        payload["live_window"] = repository.cases_live_window(
            status=status,
            decision=decision,
            search=search,
            window_seconds=recent_seconds,
        )
        payload["activities"] = repository.recent_activity(limit=activity_limit)
        return payload

    @app.get("/cases/{case_id}", tags=["cases"])
    async def get_case(case_id: str) -> dict[str, object]:
        repository: FraudRepository = app.state.repository
        payload = repository.get_case(case_id)
        if payload is None:
            raise HTTPException(status_code=404, detail="Case not found.")
        return payload

    @app.post("/cases/{case_id}/feedback", tags=["cases"])
    async def add_case_feedback(case_id: str, payload: FeedbackRequest) -> dict[str, object]:
        repository: FraudRepository = app.state.repository
        case_payload = repository.get_case(case_id)
        if case_payload is None:
            raise HTTPException(status_code=404, detail="Case not found.")
        feedback = AnalystFeedbackEvent(
            case_id=uuid.UUID(case_id),
            transaction_id=case_payload["transaction_id"],
            event_id=uuid.UUID(str(case_payload["raw_transaction"]["event_id"])),
            analyst_id=payload.analyst_id,
            feedback_label=payload.feedback_label,
            notes=payload.notes,
        )
        repository.add_feedback(feedback)
        producer: KafkaProducer = app.state.kafka_producer
        producer.send(
            app.state.settings.kafka_feedback_topic,
            key=case_id,
            value=feedback,
        )
        producer.flush(timeout=5)
        return {"status": "recorded", "feedback": feedback.model_dump(mode="json")}

    @app.get("/models/current", tags=["models"])
    async def current_model() -> dict[str, object]:
        trainer: FraudTrainer = app.state.trainer
        metadata = trainer.get_current_metadata()
        if metadata is None:
            raise HTTPException(status_code=404, detail="No registered champion model found.")
        return metadata.model_dump(mode="json")

    @app.post("/models/reload", tags=["models"])
    async def reload_model() -> dict[str, object]:
        processor: FraudStreamProcessor = app.state.processor
        loaded = processor.model_runtime.reload()
        processor.repository.cache_model_metadata(loaded.metadata)
        return {
            "status": "reloaded",
            "model": loaded.metadata.model_dump(mode="json"),
        }

    @app.get("/analytics/summary", tags=["analytics"])
    async def analytics_summary(hours: int = Query(default=24, ge=1, le=168)) -> dict[str, object]:
        repository: FraudRepository = app.state.repository
        trainer: FraudTrainer = app.state.trainer
        return {
            "overview": repository.dashboard_overview(hours=hours),
            "model": None
            if trainer.get_current_metadata() is None
            else trainer.get_current_metadata().model_dump(mode="json"),
        }

    @app.get("/analytics/trends", tags=["analytics"])
    async def analytics_trends(hours: int = Query(default=24, ge=1, le=168)) -> dict[str, object]:
        repository: FraudRepository = app.state.repository
        return {"items": repository.analytics_trends(hours=hours)}

    @app.get("/dashboard/overview", tags=["analytics"])
    async def dashboard_overview(hours: int = Query(default=24, ge=1, le=168)) -> dict[str, object]:
        repository: FraudRepository = app.state.repository
        trainer: FraudTrainer = app.state.trainer
        return {
            "summary": repository.dashboard_overview(hours=hours),
            "trends": repository.analytics_trends(hours=hours),
            "model": None
            if trainer.get_current_metadata() is None
            else trainer.get_current_metadata().model_dump(mode="json"),
            "grafana_url": app.state.settings.grafana_url,
        }

    @app.get("/dashboard/live", tags=["analytics"])
    async def dashboard_live(
        hours: int = Query(default=24, ge=1, le=168),
        recent_seconds: int = Query(default=60, ge=10, le=600),
        activity_limit: int = Query(default=8, ge=1, le=12),
    ) -> dict[str, object]:
        repository: FraudRepository = app.state.repository
        trainer: FraudTrainer = app.state.trainer
        settings: ApiSettings = app.state.settings
        return {
            "summary": repository.dashboard_overview(hours=hours),
            "recent_window": repository.recent_window_metrics(window_seconds=recent_seconds),
            "trends": repository.analytics_trends(hours=hours),
            "activities": repository.recent_activity(limit=activity_limit),
            "model": None
            if trainer.get_current_metadata() is None
            else trainer.get_current_metadata().model_dump(mode="json"),
            "grafana_url": settings.grafana_url,
            "producer": await _optional_service_json_request(
                base_url=settings.producer_internal_base_url,
                method="GET",
                path="/producer/status",
            ),
            "worker": await _optional_service_json_request(
                base_url=settings.stream_worker_internal_base_url,
                method="GET",
                path="/worker/status",
            ),
        }

    @app.get("/demo/producer/status", tags=["demo"])
    async def demo_producer_status() -> dict[str, object]:
        settings: ApiSettings = app.state.settings
        return await _service_json_request(
            base_url=settings.producer_internal_base_url,
            method="GET",
            path="/producer/status",
        )

    @app.post("/demo/producer/start", tags=["demo"])
    async def demo_producer_start() -> dict[str, object]:
        settings: ApiSettings = app.state.settings
        return await _service_json_request(
            base_url=settings.producer_internal_base_url,
            method="POST",
            path="/producer/start",
        )

    @app.post("/demo/producer/stop", tags=["demo"])
    async def demo_producer_stop() -> dict[str, object]:
        settings: ApiSettings = app.state.settings
        return await _service_json_request(
            base_url=settings.producer_internal_base_url,
            method="POST",
            path="/producer/stop",
        )

    @app.post("/demo/producer/burst", tags=["demo"])
    async def demo_producer_burst(payload: ProducerBurstRequest) -> dict[str, object]:
        settings: ApiSettings = app.state.settings
        return await _service_json_request(
            base_url=settings.producer_internal_base_url,
            method="POST",
            path="/producer/burst",
            payload=payload.model_dump(mode="json"),
        )

    @app.post("/demo/producer/boost", tags=["demo"])
    async def demo_producer_boost(payload: ProducerBoostRequest) -> dict[str, object]:
        settings: ApiSettings = app.state.settings
        return await _service_json_request(
            base_url=settings.producer_internal_base_url,
            method="POST",
            path="/producer/boost",
            payload=payload.model_dump(mode="json"),
        )

    @app.post("/demo/producer/reset", tags=["demo"])
    async def demo_producer_reset() -> dict[str, object]:
        settings: ApiSettings = app.state.settings
        return await _service_json_request(
            base_url=settings.producer_internal_base_url,
            method="POST",
            path="/producer/reset",
        )

    @app.post("/ops/grafana-alerts", tags=["ops"])
    async def receive_grafana_alert(payload: dict[str, object]) -> dict[str, object]:
        alerts = payload.get("alerts")
        alert_count = len(alerts) if isinstance(alerts, list) else 0
        statuses = (
            sorted(
                {
                    str(item.get("status"))
                    for item in alerts
                    if isinstance(item, dict) and item.get("status") is not None
                }
            )
            if isinstance(alerts, list)
            else []
        )
        logger.info(
            "received local grafana alert webhook",
            extra={
                "alert_count": alert_count,
                "statuses": statuses,
            },
        )
        return {
            "status": "accepted",
            "alert_count": alert_count,
            "statuses": statuses,
        }


def _bundle_to_response(bundle: object) -> dict[str, object]:
    validated = bundle.validated
    enriched = bundle.enriched
    scored = bundle.scored
    decision = bundle.decision
    return {
        "validated": validated.model_dump(mode="json"),
        "enriched": enriched.model_dump(mode="json"),
        "scored": scored.model_dump(mode="json"),
        "decision": decision.model_dump(mode="json"),
    }


app = build_app()


def run() -> None:
    settings = ApiSettings()
    uvicorn.run("fraud_platform_api.main:app", host=settings.host, port=settings.port, reload=False)
