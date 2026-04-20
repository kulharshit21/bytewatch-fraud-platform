from __future__ import annotations

from bytewax import operators as op
from bytewax.connectors.kafka import KafkaSink
from bytewax.connectors.kafka import operators as kop
from bytewax.dataflow import Dataflow

from fraud_platform_common.config import RuntimeSettings
from fraud_platform_stream_worker.processor import FraudStreamProcessor


def build_flow(settings: RuntimeSettings | None = None) -> Dataflow:
    settings = settings or RuntimeSettings(service_name="stream-worker")
    processor = FraudStreamProcessor(settings)
    flow = Dataflow("fraud_stream_worker")
    brokers = [settings.kafka_bootstrap_servers]

    source = kop.input(
        "raw-input",
        flow,
        brokers=brokers,
        topics=[settings.kafka_raw_topic],
        batch_size=200,
    )
    processed = op.flat_map(
        "process-events",
        source.oks,
        lambda msg: processor.process_payload(msg.value, source_topic=msg.topic or settings.kafka_raw_topic),
    )
    source_errs = op.map("source-errors", source.errs, processor.source_error_message)
    merged = op.merge("merged-output", processed, source_errs)
    op.output("kafka-output", merged, KafkaSink(brokers=brokers, topic=None))
    return flow


flow = build_flow()
