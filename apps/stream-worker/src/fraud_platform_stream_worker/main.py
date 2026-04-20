from __future__ import annotations

import threading
import uvicorn
from fastapi import FastAPI

from fraud_platform_common.config import RuntimeSettings
from fraud_platform_common.service import create_service_app, dependency_from_hostport, dependency_from_url
from fraud_platform_stream_worker.runtime import WorkerRuntime, monitor_runtime


class StreamWorkerSettings(RuntimeSettings):
    service_name: str = "stream-worker"
    host: str = "0.0.0.0"

    def __init__(self, **values: object) -> None:
        super().__init__(**values)
        self.port = self.stream_worker_port


def _start_worker(app: FastAPI) -> None:
    settings: StreamWorkerSettings = app.state.settings
    runtime = WorkerRuntime(settings)
    app.state.runtime = runtime
    app.state.worker_ready = False

    if settings.stream_autostart:
        runtime.start()

    def set_ready(value: bool) -> None:
        app.state.worker_ready = value

    monitor = threading.Thread(
        target=monitor_runtime,
        args=(runtime, set_ready),
        name="worker-health-monitor",
        daemon=True,
    )
    monitor.start()
    app.state.monitor_thread = monitor


def _shutdown_worker(app: FastAPI) -> None:
    runtime: WorkerRuntime | None = getattr(app.state, "runtime", None)
    if runtime:
        runtime.stop()
    app.state.worker_ready = False


def build_app() -> FastAPI:
    settings = StreamWorkerSettings()
    app = create_service_app(
        settings=settings,
        description="Bytewax stream worker consuming tx.raw and emitting validated, enriched, scored, and decision events.",
        dependencies=[
            dependency_from_hostport("kafka", settings.kafka_bootstrap_servers, 9092),
            dependency_from_url("redis", settings.redis_url, 6379),
            dependency_from_url("postgres", settings.database_url, 5432),
            dependency_from_url("mlflow", settings.mlflow_tracking_uri, 5000, required=False),
        ],
        extra_metadata={
            "role": "bytewax fraud stream processing",
            "stream_engine": "bytewax",
            "topics": [
                settings.kafka_raw_topic,
                settings.kafka_validated_topic,
                settings.kafka_enriched_topic,
                settings.kafka_scored_topic,
                settings.kafka_decisions_topic,
                settings.kafka_dlq_topic,
            ],
        },
        startup_callbacks=[_start_worker],
        shutdown_callbacks=[_shutdown_worker],
    )
    runtime_routes(app)
    return app


def runtime_routes(app: FastAPI) -> None:
    @app.get("/worker/status", tags=["worker"])
    async def worker_status() -> dict[str, object]:
        runtime: WorkerRuntime = app.state.runtime
        return {
            "running": runtime.status.running,
            "started_at": None if runtime.status.started_at is None else runtime.status.started_at.isoformat(),
            "last_error": runtime.status.last_error,
            "healthy": runtime.healthy(),
        }

    @app.post("/worker/start", tags=["worker"])
    async def worker_start() -> dict[str, str]:
        runtime: WorkerRuntime = app.state.runtime
        runtime.start()
        return {"status": "started"}


app = build_app()


def run() -> None:
    settings = StreamWorkerSettings()
    uvicorn.run("fraud_platform_stream_worker.main:app", host=settings.host, port=settings.port, reload=False)
