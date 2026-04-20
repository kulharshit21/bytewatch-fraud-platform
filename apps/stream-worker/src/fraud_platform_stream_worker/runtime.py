from __future__ import annotations

import threading
import time
from dataclasses import dataclass
from datetime import UTC, datetime

from fraud_platform_common.config import RuntimeSettings

try:
    from bytewax.run import cli_main as run_flow
except ImportError:  # pragma: no cover - compatibility fallback
    from bytewax._bytewax import cli_main as run_flow  # type: ignore[attr-defined]


@dataclass(slots=True)
class WorkerStatus:
    running: bool = False
    started_at: datetime | None = None
    last_error: str | None = None


class WorkerRuntime:
    def __init__(self, settings: RuntimeSettings) -> None:
        self.settings = settings
        self.status = WorkerStatus()
        self._thread: threading.Thread | None = None
        self._last_exception: Exception | None = None

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self.status.running = True
        self.status.started_at = datetime.now(UTC)
        self.status.last_error = None
        self._thread = threading.Thread(target=self._run, name="bytewax-worker", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self.status.running = False

    def healthy(self) -> bool:
        return bool(
            self.status.running
            and self._thread
            and self._thread.is_alive()
            and self._last_exception is None
        )

    def _run(self) -> None:
        try:
            from fraud_platform_stream_worker.flow import build_flow

            run_flow(build_flow(self.settings))
        except Exception as exc:  # pragma: no cover - runtime protection
            self._last_exception = exc
            self.status.last_error = str(exc)
            self.status.running = False


def monitor_runtime(runtime: WorkerRuntime, set_ready: callable) -> None:
    while True:
        set_ready(runtime.healthy())
        time.sleep(2)
