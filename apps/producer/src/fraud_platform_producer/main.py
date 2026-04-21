from __future__ import annotations

import uvicorn
from fastapi import FastAPI
from fraud_platform_common.config import RuntimeSettings
from fraud_platform_common.service import create_service_app, dependency_from_hostport
from fraud_platform_contracts import SimulationScenario
from pydantic import BaseModel, Field

from fraud_platform_producer.runtime import ProducerRuntime


class ProducerBurstRequest(BaseModel):
    scenario: SimulationScenario
    count: int = Field(default=12, ge=1, le=100)


class ProducerBoostRequest(BaseModel):
    fraud_ratio: float = Field(default=0.6, ge=0.01, le=0.95)
    rate_per_second: float | None = Field(default=6.0, ge=0.1, le=25.0)
    duration_seconds: int = Field(default=30, ge=5, le=300)


class ProducerSettings(RuntimeSettings):
    service_name: str = "producer"
    host: str = "0.0.0.0"

    def __init__(self, **values: object) -> None:
        super().__init__(**values)
        self.port = self.producer_port


def _build_runtime(app: FastAPI) -> None:
    settings: ProducerSettings = app.state.settings
    runtime = ProducerRuntime(settings)
    app.state.runtime = runtime
    if settings.producer_autostart:
        runtime.start()


def _shutdown_runtime(app: FastAPI) -> None:
    runtime: ProducerRuntime | None = getattr(app.state, "runtime", None)
    if runtime:
        runtime.stop()


def build_app() -> FastAPI:
    settings = ProducerSettings()
    app = create_service_app(
        settings=settings,
        description="Synthetic transaction producer with Kafka publishing and dataset export.",
        dependencies=[dependency_from_hostport("kafka", settings.kafka_bootstrap_servers, 9092)],
        extra_metadata={
            "role": "generates synthetic transactions and publishes them to tx.raw",
            "mode": "service",
        },
        startup_callbacks=[_build_runtime],
        shutdown_callbacks=[_shutdown_runtime],
    )
    runtime_routes(app)
    return app


def runtime_routes(app: FastAPI) -> None:
    @app.get("/producer/status", tags=["producer"])
    async def producer_status() -> dict[str, object]:
        runtime: ProducerRuntime = app.state.runtime
        return {
            "running": runtime.stats.running,
            "generated_events": runtime.stats.generated_events,
            "started_at": None
            if runtime.stats.started_at is None
            else runtime.stats.started_at.isoformat(),
            "rate_per_second": app.state.settings.producer_rate_per_second,
            "fraud_ratio": app.state.settings.producer_fraud_ratio,
            "current_rate_per_second": runtime.stats.current_rate_per_second,
            "current_fraud_ratio": runtime.stats.current_fraud_ratio,
            "override_expires_at": None
            if runtime.stats.override_expires_at is None
            else runtime.stats.override_expires_at.isoformat(),
        }

    @app.post("/producer/start", tags=["producer"])
    async def producer_start() -> dict[str, str]:
        runtime: ProducerRuntime = app.state.runtime
        runtime.start()
        return {"status": "started"}

    @app.post("/producer/stop", tags=["producer"])
    async def producer_stop() -> dict[str, str]:
        runtime: ProducerRuntime = app.state.runtime
        runtime.stop()
        return {"status": "stopped"}

    @app.post("/producer/burst", tags=["producer"])
    async def producer_burst(payload: ProducerBurstRequest) -> dict[str, object]:
        runtime: ProducerRuntime = app.state.runtime
        events = runtime.inject_burst(scenario=payload.scenario, events=payload.count)
        return {
            "status": "published",
            "scenario": payload.scenario,
            "count": len(events),
            "transaction_ids": [event.transaction_id for event in events],
        }

    @app.post("/producer/boost", tags=["producer"])
    async def producer_boost(payload: ProducerBoostRequest) -> dict[str, object]:
        runtime: ProducerRuntime = app.state.runtime
        runtime.apply_temporary_profile(
            fraud_ratio=payload.fraud_ratio,
            rate_per_second=payload.rate_per_second,
            duration_seconds=payload.duration_seconds,
        )
        return {
            "status": "boosted",
            "fraud_ratio": runtime.stats.current_fraud_ratio,
            "rate_per_second": runtime.stats.current_rate_per_second,
            "duration_seconds": payload.duration_seconds,
            "override_expires_at": None
            if runtime.stats.override_expires_at is None
            else runtime.stats.override_expires_at.isoformat(),
        }

    @app.post("/producer/reset", tags=["producer"])
    async def producer_reset() -> dict[str, object]:
        runtime: ProducerRuntime = app.state.runtime
        runtime.reset_profile()
        return {
            "status": "reset",
            "fraud_ratio": runtime.stats.current_fraud_ratio,
            "rate_per_second": runtime.stats.current_rate_per_second,
        }

    @app.post("/producer/export", tags=["producer"])
    async def producer_export(events: int = 3000) -> dict[str, str]:
        runtime: ProducerRuntime = app.state.runtime
        return {"path": runtime.export_dataset(app.state.settings.producer_export_path, events)}


app = build_app()


def run() -> None:
    settings = ProducerSettings()
    uvicorn.run(
        "fraud_platform_producer.main:app", host=settings.host, port=settings.port, reload=False
    )
