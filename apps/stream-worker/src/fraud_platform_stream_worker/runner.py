from __future__ import annotations

from fraud_platform_common.config import RuntimeSettings

try:
    from bytewax.run import cli_main as run_flow
except ImportError:  # pragma: no cover - compatibility fallback
    from bytewax._bytewax import cli_main as run_flow  # type: ignore[attr-defined]

from fraud_platform_stream_worker.flow import build_flow


def main() -> None:
    settings = RuntimeSettings(service_name="stream-worker")
    run_flow(build_flow(settings))


if __name__ == "__main__":
    main()
