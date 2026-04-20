from __future__ import annotations

import argparse
import json
from dataclasses import asdict, is_dataclass

from fraud_platform_common.config import RuntimeSettings

from fraud_platform_trainer.training import FraudTrainer


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Fraud platform trainer CLI")
    subparsers = parser.add_subparsers(dest="command", required=True)

    bootstrap = subparsers.add_parser(
        "bootstrap-model", help="Train and register a champion model if one does not exist."
    )
    bootstrap.add_argument(
        "--force", action="store_true", help="Retrain even if a champion alias already exists."
    )

    train_csv = subparsers.add_parser("train-csv", help="Train from a CSV export.")
    train_csv.add_argument("--dataset", required=True, help="Path to CSV dataset.")
    train_csv.add_argument("--alias", default=None, help="Alias to assign.")

    drift = subparsers.add_parser("drift-report", help="Generate an Evidently drift report.")
    drift.add_argument("--sample-size", type=int, default=500)

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    settings = RuntimeSettings(service_name="trainer")
    trainer = FraudTrainer(settings)

    if args.command == "bootstrap-model":
        result = trainer.bootstrap_model(force=args.force)
    elif args.command == "train-csv":
        result = trainer.train_from_csv(
            args.dataset, alias=args.alias or settings.mlflow_champion_alias
        )
    else:
        result = trainer.generate_drift_report(sample_size=args.sample_size)

    print(json.dumps(_serialize(result), indent=2))


def _serialize(payload: object) -> object:
    if hasattr(payload, "model_dump"):
        return payload.model_dump(mode="json")  # type: ignore[no-any-return]
    if is_dataclass(payload):
        return _serialize(asdict(payload))
    if hasattr(payload, "__dict__"):
        return {
            key: _serialize(value)
            for key, value in payload.__dict__.items()
            if not key.startswith("_")
        }
    if isinstance(payload, dict):
        return {key: _serialize(value) for key, value in payload.items()}
    if isinstance(payload, list):
        return [_serialize(item) for item in payload]
    return payload


if __name__ == "__main__":
    main()
