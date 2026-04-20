import logging
import socket
import time
import uuid
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any
from urllib.parse import urlparse

from fastapi import FastAPI, Request
from fastapi.responses import ORJSONResponse, PlainTextResponse

from fraud_platform_common.config import RuntimeSettings
from fraud_platform_common.logging import configure_logging
from fraud_platform_contracts import DependencyStatus, HealthResponse
from fraud_platform_observability.metrics import (
    HTTP_REQUEST_COUNTER,
    HTTP_REQUEST_DURATION_SECONDS,
    render_metrics,
)

LOGGER = logging.getLogger(__name__)
LifecycleCallback = Any


@dataclass(frozen=True)
class DependencyTarget:
    name: str
    host: str
    port: int
    required: bool = True


def dependency_from_url(name: str, value: str, default_port: int, required: bool = True) -> DependencyTarget:
    parsed = urlparse(value)
    host = parsed.hostname or "localhost"
    port = parsed.port or default_port
    return DependencyTarget(name=name, host=host, port=port, required=required)


def dependency_from_hostport(
    name: str, value: str, default_port: int, required: bool = True
) -> DependencyTarget:
    if "://" in value:
        return dependency_from_url(name=name, value=value, default_port=default_port, required=required)

    host, _, port = value.partition(":")
    return DependencyTarget(
        name=name,
        host=host or "localhost",
        port=int(port or default_port),
        required=required,
    )


def _probe_dependency(target: DependencyTarget, timeout_seconds: float = 1.0) -> DependencyStatus:
    try:
        with socket.create_connection((target.host, target.port), timeout=timeout_seconds):
            return DependencyStatus(name=target.name, healthy=True, host=target.host, port=target.port)
    except OSError as exc:
        return DependencyStatus(
            name=target.name,
            healthy=not target.required,
            host=target.host,
            port=target.port,
            detail=str(exc),
        )


def create_service_app(
    *,
    settings: RuntimeSettings,
    description: str,
    dependencies: Sequence[DependencyTarget] | None = None,
    extra_metadata: dict[str, Any] | None = None,
    startup_callbacks: Sequence[LifecycleCallback] | None = None,
    shutdown_callbacks: Sequence[LifecycleCallback] | None = None,
) -> FastAPI:
    configure_logging(settings.service_name, settings.log_level)
    dependencies = dependencies or []
    extra_metadata = extra_metadata or {}
    startup_callbacks = startup_callbacks or []
    shutdown_callbacks = shutdown_callbacks or []

    app = FastAPI(
        title=f"{settings.service_name} service",
        version=settings.version,
        description=description,
        default_response_class=ORJSONResponse,
    )
    app.state.settings = settings
    app.state.dependencies = list(dependencies)
    app.state.worker_ready = True

    @app.middleware("http")
    async def request_context_middleware(request: Request, call_next):  # type: ignore[no-untyped-def]
        request_id = request.headers.get("x-request-id", str(uuid.uuid4()))
        started = time.perf_counter()
        response = await call_next(request)
        duration = time.perf_counter() - started
        status_code = response.status_code

        HTTP_REQUEST_COUNTER.labels(
            service=settings.service_name,
            method=request.method,
            path=request.url.path,
            status_code=str(status_code),
        ).inc()
        HTTP_REQUEST_DURATION_SECONDS.labels(
            service=settings.service_name,
            method=request.method,
            path=request.url.path,
        ).observe(duration)

        LOGGER.info(
            "request completed",
            extra={
                "request_id": request_id,
                "method": request.method,
                "path": request.url.path,
                "status_code": status_code,
                "duration_ms": round(duration * 1000, 2),
            },
        )
        response.headers["x-request-id"] = request_id
        return response

    @app.get("/", tags=["meta"])
    async def describe_service() -> dict[str, Any]:
        return {
            "service": settings.service_name,
            "environment": settings.app_env,
            "version": settings.version,
            "dependencies": [target.name for target in dependencies],
            "metadata": extra_metadata,
            "worker_ready": app.state.worker_ready,
        }

    @app.get("/health/live", response_model=HealthResponse, tags=["health"])
    async def live() -> HealthResponse:
        return HealthResponse(
            service=settings.service_name,
            version=settings.version,
            status="live",
            checked_at=datetime.now(timezone.utc),
            dependencies=[],
        )

    @app.get("/health/ready", response_model=HealthResponse, tags=["health"])
    async def ready() -> ORJSONResponse:
        statuses = [_probe_dependency(target) for target in dependencies]
        is_healthy = all(status.healthy for status in statuses) and bool(app.state.worker_ready)
        response = HealthResponse(
            service=settings.service_name,
            version=settings.version,
            status="ready" if is_healthy else "degraded",
            checked_at=datetime.now(timezone.utc),
            dependencies=statuses,
        )
        return ORJSONResponse(status_code=200 if is_healthy else 503, content=response.model_dump(mode="json"))

    @app.get("/metrics", include_in_schema=False)
    async def metrics() -> PlainTextResponse:
        return render_metrics()

    @app.on_event("startup")
    async def startup_event() -> None:
        for callback in startup_callbacks:
            result = callback(app)
            if hasattr(result, "__await__"):
                await result

    @app.on_event("shutdown")
    async def shutdown_event() -> None:
        for callback in shutdown_callbacks:
            result = callback(app)
            if hasattr(result, "__await__"):
                await result

    return app
