from __future__ import annotations

import ast
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import mlflow
import mlflow.sklearn
import numpy as np
import pandas as pd
from evidently import Report
from evidently.presets import DataDriftPreset
from mlflow import MlflowClient
from sklearn.metrics import (
    average_precision_score,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)
from xgboost import XGBClassifier

from fraud_platform_common.config import RuntimeSettings
from fraud_platform_contracts import ModelMetadata, TransactionEvent, load_json
from fraud_platform_feature_engineering import MODEL_FEATURE_FIELDS, compute_feature_values
from fraud_platform_feature_store import MemoryFeatureStore
from fraud_platform_observability.metrics import DRIFT_SCORE_GAUGE
from fraud_platform_persistence import FraudRepository
from fraud_platform_producer.generation import SyntheticTransactionGenerator


@dataclass(slots=True)
class TrainingArtifacts:
    dataset_path: str
    metadata: ModelMetadata
    metrics: dict[str, float]
    thresholds: dict[str, float]
    drift_report_html: str | None = None
    drift_report_json: str | None = None


class FraudTrainer:
    def __init__(self, settings: RuntimeSettings) -> None:
        self.settings = settings
        self.repository = FraudRepository(settings)
        mlflow.set_tracking_uri(settings.mlflow_tracking_uri)

    def bootstrap_model(self, minimum_events: int = 3000, force: bool = False) -> TrainingArtifacts:
        if not force:
            existing = self.get_current_metadata()
            if existing is not None:
                return TrainingArtifacts(
                    dataset_path=self.settings.producer_export_path,
                    metadata=existing,
                    metrics=existing.metrics,
                    thresholds={
                        "review_threshold": existing.review_threshold,
                        "block_threshold": existing.block_threshold,
                    },
                )

        dataset_path = self._ensure_dataset(minimum_events)
        return self.train_from_csv(dataset_path, alias=self.settings.mlflow_champion_alias)

    def train_from_csv(self, dataset_path: str, alias: str) -> TrainingArtifacts:
        events = self._load_events_from_csv(dataset_path)
        feature_frame = self._build_feature_frame(events)
        return self._train(feature_frame, dataset_path=dataset_path, alias=alias)

    def train_from_repository(self, alias: str | None = None) -> TrainingArtifacts:
        raw_rows = self.repository.training_frame()
        events = [
            self._coerce_transaction_event(row)
            for row in raw_rows
            if row.get("label") is not None
        ]
        if len(events) < 200:
            dataset_path = self._ensure_dataset(3000)
            return self.train_from_csv(dataset_path, alias=alias or self.settings.mlflow_champion_alias)
        frame = self._build_feature_frame(events)
        return self._train(
            frame,
            dataset_path="database://transactions_raw",
            alias=alias or self.settings.mlflow_champion_alias,
        )

    def generate_drift_report(self, sample_size: int = 500) -> dict[str, Any]:
        dataset_path = self._ensure_dataset(max(1000, sample_size * 2))
        reference_events = self._load_events_from_csv(dataset_path)
        current_rows = self.repository.training_frame()[-sample_size:]
        current_events = [
            self._coerce_transaction_event(row)
            for row in current_rows
            if row.get("label") is not None
        ]
        if len(current_events) < 50:
            current_events = reference_events[-sample_size:]

        reference_df = self._build_feature_frame(reference_events).tail(sample_size).reset_index(drop=True)
        current_df = self._build_feature_frame(current_events).tail(sample_size).reset_index(drop=True)

        output_dir = Path(self.settings.data_dir) / "drift"
        output_dir.mkdir(parents=True, exist_ok=True)
        html_path = output_dir / "latest_drift_report.html"
        json_path = output_dir / "latest_drift_report.json"

        report = Report([DataDriftPreset()])
        evaluation = report.run(current_data=current_df, reference_data=reference_df)
        evaluation.save_html(str(html_path))
        evaluation.save_json(str(json_path))
        report_dict = evaluation.dict()
        score = self._extract_drift_score(report_dict)
        DRIFT_SCORE_GAUGE.labels(metric="dataset_drift_score").set(score)
        return {
            "html_path": str(html_path),
            "json_path": str(json_path),
            "dataset_drift_score": score,
        }

    def get_current_metadata(self) -> ModelMetadata | None:
        cached = self.repository.get_current_model(self.settings.mlflow_champion_alias)
        if cached:
            return ModelMetadata.model_validate(cached)
        client = MlflowClient(tracking_uri=self.settings.mlflow_tracking_uri)
        try:
            version = client.get_model_version_by_alias(
                self.settings.mlflow_model_name,
                self.settings.mlflow_champion_alias,
            )
        except Exception:
            return None
        return ModelMetadata(
            model_name=self.settings.mlflow_model_name,
            model_version=str(version.version),
            model_alias=self.settings.mlflow_champion_alias,
            review_threshold=self.settings.model_review_threshold,
            block_threshold=self.settings.model_block_threshold,
            run_id=version.run_id,
        )

    def _ensure_dataset(self, minimum_events: int) -> str:
        output = Path(self.settings.producer_export_path)
        if output.exists():
            return str(output)
        generator = SyntheticTransactionGenerator(
            seed=self.settings.producer_random_seed,
            fraud_ratio=self.settings.producer_fraud_ratio,
        )
        return generator.export_dataset(str(output), minimum_events)

    def _load_events_from_csv(self, dataset_path: str) -> list[TransactionEvent]:
        frame = pd.read_csv(dataset_path)
        records = frame.to_dict(orient="records")
        return [self._coerce_transaction_event(row) for row in records]

    @staticmethod
    def _coerce_transaction_event(payload: dict[str, Any]) -> TransactionEvent:
        normalized = dict(payload)
        metadata = normalized.get("metadata")
        if isinstance(metadata, str) and metadata:
            try:
                normalized["metadata"] = json.loads(metadata)
            except json.JSONDecodeError:
                normalized["metadata"] = ast.literal_eval(metadata)

        allowed_fields = TransactionEvent.model_fields.keys()
        filtered = {key: value for key, value in normalized.items() if key in allowed_fields}
        return load_json(TransactionEvent, filtered)

    def _build_feature_frame(self, events: list[TransactionEvent]) -> pd.DataFrame:
        store = MemoryFeatureStore()
        rows: list[dict[str, Any]] = []
        for event in sorted(events, key=lambda item: item.event_time):
            if not store.claim_event(event.event_id):
                continue
            context = store.get_context(event)
            features = compute_feature_values(event, context)
            rows.append(
                {
                    **features,
                    "label": int(event.label or 0),
                    "event_time": event.event_time,
                    "simulation_scenario": event.simulation_scenario,
                }
            )
            store.update_state(event)
        return pd.DataFrame(rows)

    def _train(self, feature_frame: pd.DataFrame, *, dataset_path: str, alias: str) -> TrainingArtifacts:
        if feature_frame.empty:
            raise ValueError("No feature rows available for training.")

        feature_frame = feature_frame.sort_values("event_time").reset_index(drop=True)
        split_index = max(int(len(feature_frame) * 0.8), 1)
        train_df = feature_frame.iloc[:split_index]
        test_df = feature_frame.iloc[split_index:]
        if test_df.empty:
            test_df = train_df.tail(min(200, len(train_df))).copy()

        x_train = train_df[MODEL_FEATURE_FIELDS]
        y_train = train_df["label"].astype(int)
        x_test = test_df[MODEL_FEATURE_FIELDS]
        y_test = test_df["label"].astype(int)

        positives = max(int(y_train.sum()), 1)
        negatives = max(len(y_train) - positives, 1)
        scale_pos_weight = negatives / positives

        params = {
            "n_estimators": 220,
            "max_depth": 5,
            "learning_rate": 0.08,
            "subsample": 0.9,
            "colsample_bytree": 0.9,
            "min_child_weight": 2,
            "reg_lambda": 1.0,
            "random_state": self.settings.producer_random_seed,
            "eval_metric": "logloss",
            "tree_method": "hist",
            "scale_pos_weight": scale_pos_weight,
        }
        model = XGBClassifier(**params)
        model.fit(x_train, y_train)

        probabilities = model.predict_proba(x_test)[:, 1]
        sweep = self._threshold_sweep(y_test.to_numpy(), probabilities)
        review_threshold = float(sweep["best_f1_threshold"])
        block_threshold = float(sweep["high_precision_threshold"])

        predictions = (probabilities >= review_threshold).astype(int)
        metrics = {
            "precision": float(precision_score(y_test, predictions, zero_division=0)),
            "recall": float(recall_score(y_test, predictions, zero_division=0)),
            "f1": float(f1_score(y_test, predictions, zero_division=0)),
            "pr_auc": float(average_precision_score(y_test, probabilities)),
            "roc_auc": float(roc_auc_score(y_test, probabilities)),
        }
        cm = confusion_matrix(y_test, predictions).tolist()

        client = MlflowClient(tracking_uri=self.settings.mlflow_tracking_uri)
        with mlflow.start_run(run_name=f"fraud-xgb-{alias}") as run:
            mlflow.log_params({**params, "dataset_path": dataset_path, "alias_target": alias})
            mlflow.log_metrics(metrics)
            mlflow.log_dict({"threshold_sweep": sweep, "confusion_matrix": cm}, "evaluation.json")
            mlflow.sklearn.log_model(
                sk_model=model,
                artifact_path="model",
                input_example=x_train.head(5),
                registered_model_name=self.settings.mlflow_model_name,
            )

            version = self._lookup_model_version(client, run.info.run_id, self.settings.mlflow_model_name)
            client.set_registered_model_alias(
                self.settings.mlflow_model_name,
                alias,
                version,
            )
            metadata = ModelMetadata(
                model_name=self.settings.mlflow_model_name,
                model_version=str(version),
                model_alias=alias,
                review_threshold=review_threshold,
                block_threshold=block_threshold,
                run_id=run.info.run_id,
                metrics=metrics,
            )
            metadata_payload = {
                **metadata.model_dump(mode="json"),
                "feature_names": MODEL_FEATURE_FIELDS,
            }
            mlflow.log_dict(metadata_payload, "model_metadata.json")

        self.repository.cache_model_metadata(metadata)
        drift = self.generate_drift_report()
        return TrainingArtifacts(
            dataset_path=dataset_path,
            metadata=metadata,
            metrics=metrics,
            thresholds={
                "review_threshold": review_threshold,
                "block_threshold": block_threshold,
            },
            drift_report_html=drift["html_path"],
            drift_report_json=drift["json_path"],
        )

    @staticmethod
    def _lookup_model_version(client: MlflowClient, run_id: str, model_name: str) -> int:
        versions = client.search_model_versions(f"name='{model_name}'")
        matching = [item for item in versions if item.run_id == run_id]
        if not matching:
            raise ValueError(f"No registered model version found for run {run_id}")
        latest = sorted(matching, key=lambda item: int(item.version), reverse=True)[0]
        return int(latest.version)

    @staticmethod
    def _threshold_sweep(y_true: np.ndarray, probabilities: np.ndarray) -> dict[str, Any]:
        rows: list[dict[str, float]] = []
        for threshold in np.linspace(0.1, 0.95, 18):
            pred = (probabilities >= threshold).astype(int)
            rows.append(
                {
                    "threshold": float(threshold),
                    "precision": float(precision_score(y_true, pred, zero_division=0)),
                    "recall": float(recall_score(y_true, pred, zero_division=0)),
                    "f1": float(f1_score(y_true, pred, zero_division=0)),
                }
            )
        best_f1 = max(rows, key=lambda row: row["f1"])
        precision_candidates = [row for row in rows if row["precision"] >= 0.85]
        best_precision = precision_candidates[-1] if precision_candidates else max(rows, key=lambda row: row["precision"])
        return {
            "rows": rows,
            "best_f1_threshold": best_f1["threshold"],
            "high_precision_threshold": min(
                0.99,
                max(best_f1["threshold"] + 0.1, best_precision["threshold"]),
            ),
        }

    @staticmethod
    def _extract_drift_score(payload: dict[str, Any]) -> float:
        serialized = json.dumps(payload)
        for key in ("share_of_drifted_columns", "dataset_drift_score", "drift_share"):
            marker = f'"{key}":'
            if marker in serialized:
                suffix = serialized.split(marker, maxsplit=1)[1]
                numeric = []
                for char in suffix:
                    if char.isdigit() or char in ".-":
                        numeric.append(char)
                    elif numeric:
                        break
                if numeric:
                    return float("".join(numeric))
        return 0.0
