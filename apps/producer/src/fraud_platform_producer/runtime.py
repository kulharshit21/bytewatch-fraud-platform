from __future__ import annotations

import threading
import time
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path

from fraud_platform_common.config import RuntimeSettings
from fraud_platform_contracts import SimulationScenario, TransactionEvent, dump_json
from fraud_platform_observability.metrics import PRODUCER_EVENTS_COUNTER
from kafka import KafkaProducer

from fraud_platform_producer.generation import SyntheticTransactionGenerator


@dataclass(slots=True)
class ProducerStats:
    generated_events: int = 0
    started_at: datetime | None = None
    running: bool = False
    current_rate_per_second: float = 0.0
    current_fraud_ratio: float = 0.0
    override_expires_at: datetime | None = None


class ProducerRuntime:
    def __init__(self, settings: RuntimeSettings) -> None:
        self.settings = settings
        self.generator = SyntheticTransactionGenerator(
            seed=settings.producer_random_seed,
            fraud_ratio=settings.producer_fraud_ratio,
        )
        self.stats = ProducerStats(
            current_rate_per_second=settings.producer_rate_per_second,
            current_fraud_ratio=settings.producer_fraud_ratio,
        )
        self._thread: threading.Thread | None = None
        self._stop_event = threading.Event()
        self._producer: KafkaProducer | None = None
        self._profile_lock = threading.Lock()
        self._default_rate_per_second = settings.producer_rate_per_second
        self._default_fraud_ratio = settings.producer_fraud_ratio
        self._current_rate_per_second = settings.producer_rate_per_second
        self._current_fraud_ratio = settings.producer_fraud_ratio
        self._override_expires_at: datetime | None = None

    def _get_producer(self) -> KafkaProducer:
        if self._producer is None:
            self._producer = KafkaProducer(
                bootstrap_servers=self.settings.kafka_bootstrap_servers,
                value_serializer=lambda event: dump_json(event),
                key_serializer=lambda value: value.encode("utf-8"),
                linger_ms=100,
            )
        return self._producer

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._stop_event.clear()
        self.stats.running = True
        self.stats.started_at = datetime.now(UTC)
        self._thread = threading.Thread(target=self._run_loop, name="producer-runtime", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop_event.set()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=3)
        if self._producer is not None:
            self._producer.flush(timeout=5)
            self._producer.close(timeout=5)
            self._producer = None
        self.stats.running = False

    def export_dataset(self, output_path: str, events: int) -> str:
        return self.generator.export_dataset(output_path=output_path, events=events)

    def generate_once(self) -> TransactionEvent:
        event = self.generator.generate()
        self.publish(event)
        return event

    def inject_burst(self, *, scenario: SimulationScenario, events: int) -> list[TransactionEvent]:
        published: list[TransactionEvent] = []
        for _ in range(max(1, events)):
            event = self.generator.generate(now=datetime.now(UTC), scenario=scenario)
            self.publish(event)
            published.append(event)
        return published

    def apply_temporary_profile(
        self,
        *,
        fraud_ratio: float | None = None,
        rate_per_second: float | None = None,
        duration_seconds: int = 30,
    ) -> None:
        with self._profile_lock:
            if fraud_ratio is not None:
                self._current_fraud_ratio = max(0.01, min(fraud_ratio, 0.95))
                self.generator.set_fraud_ratio(self._current_fraud_ratio)
            if rate_per_second is not None:
                self._current_rate_per_second = max(0.1, rate_per_second)
            self._override_expires_at = datetime.now(UTC).replace(microsecond=0) + timedelta(
                seconds=max(1, duration_seconds)
            )
            self._sync_stats_locked()

    def reset_profile(self) -> None:
        with self._profile_lock:
            self._current_rate_per_second = self._default_rate_per_second
            self._current_fraud_ratio = self._default_fraud_ratio
            self.generator.set_fraud_ratio(self._current_fraud_ratio)
            self._override_expires_at = None
            self._sync_stats_locked()

    def publish(self, event: TransactionEvent) -> None:
        producer = self._get_producer()
        producer.send(
            self.settings.kafka_raw_topic,
            key=event.account_id,
            value=event,
        )
        producer.flush(timeout=5)
        label = "fraud" if event.label else "legit"
        PRODUCER_EVENTS_COUNTER.labels(
            scenario=event.simulation_scenario,
            label=label,
        ).inc()
        self.stats.generated_events += 1

    def _run_loop(self) -> None:
        max_events = self.settings.producer_max_events
        while not self._stop_event.is_set():
            self._expire_profile_if_needed()
            event = self.generator.generate()
            self.publish(event)
            if max_events and self.stats.generated_events >= max_events:
                self.stop()
                return
            time.sleep(max(0.05, 1.0 / self.current_rate_per_second))

    def bootstrap_dataset_if_missing(self, minimum_events: int = 3000) -> str:
        output = Path(self.settings.producer_export_path)
        if output.exists():
            return str(output)
        return self.export_dataset(str(output), minimum_events)

    @property
    def current_rate_per_second(self) -> float:
        with self._profile_lock:
            self._expire_profile_if_needed_locked()
            return self._current_rate_per_second

    def _expire_profile_if_needed(self) -> None:
        with self._profile_lock:
            self._expire_profile_if_needed_locked()

    def _expire_profile_if_needed_locked(self) -> None:
        if self._override_expires_at and datetime.now(UTC) >= self._override_expires_at:
            self._current_rate_per_second = self._default_rate_per_second
            self._current_fraud_ratio = self._default_fraud_ratio
            self.generator.set_fraud_ratio(self._current_fraud_ratio)
            self._override_expires_at = None
            self._sync_stats_locked()

    def _sync_stats_locked(self) -> None:
        self.stats.current_rate_per_second = self._current_rate_per_second
        self.stats.current_fraud_ratio = self._current_fraud_ratio
        self.stats.override_expires_at = self._override_expires_at
