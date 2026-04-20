from __future__ import annotations

import argparse

from fraud_platform_common.config import RuntimeSettings
from fraud_platform_producer.runtime import ProducerRuntime


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Synthetic fraud transaction producer CLI")
    subcommands = parser.add_subparsers(dest="command", required=True)

    export = subcommands.add_parser("export-dataset", help="Export synthetic transactions to CSV")
    export.add_argument("--output", required=True)
    export.add_argument("--events", type=int, default=3000)

    publish_once = subcommands.add_parser("publish-once", help="Publish a single transaction to Kafka")
    publish_once.add_argument("--count", type=int, default=1)
    return parser


def main() -> None:
    args = build_parser().parse_args()
    settings = RuntimeSettings(service_name="producer-cli")
    runtime = ProducerRuntime(settings)
    if args.command == "export-dataset":
        output = runtime.export_dataset(args.output, args.events)
        print(output)
        return
    for _ in range(args.count):
        event = runtime.generate_once()
        print(event.transaction_id)
