from __future__ import annotations

import threading
import time
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from kafka import KafkaProducer

from fraud_platform_common.config import RuntimeSettings
from fraud_platform_contracts import TransactionEvent, dump_json
from fraud_platform_observability.metrics import PRODUCER_EVENTS_COUNTER
from fraud_platform_producer.generation import SyntheticTransactionGenerator


@dataclass(slots=True)
class ProducerStats:
    generated_events: int = 0
    started_at: datetime | None = None
    running: bool = False


class ProducerRuntime:
    def __init__(self, settings: RuntimeSettings) -> None:
        self.settings = settings
        self.generator = SyntheticTransactionGenerator(
            seed=settings.producer_random_seed,
            fraud_ratio=settings.producer_fraud_ratio,
        )
        self.stats = ProducerStats()
        self._thread: threading.Thread | None = None
        self._stop_event = threading.Event()
        self._producer: KafkaProducer | None = None

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
            event = self.generator.generate()
            self.publish(event)
            if max_events and self.stats.generated_events >= max_events:
                self.stop()
                return
            time.sleep(max(0.05, 1.0 / max(self.settings.producer_rate_per_second, 0.1)))

    def bootstrap_dataset_if_missing(self, minimum_events: int = 3000) -> str:
        output = Path(self.settings.producer_export_path)
        if output.exists():
            return str(output)
        return self.export_dataset(str(output), minimum_events)
