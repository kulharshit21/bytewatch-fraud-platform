from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import mlflow
import mlflow.artifacts
import mlflow.sklearn
import pandas as pd
from fraud_platform_common.config import RuntimeSettings
from fraud_platform_contracts import (
    FraudDecision,
    ModelMetadata,
    ReasonCode,
    RuleHit,
)
from fraud_platform_feature_engineering import MODEL_FEATURE_FIELDS
from fraud_platform_observability.metrics import (
    MODEL_INFO_GAUGE,
    MODEL_PREDICTION_COUNTER,
    MODEL_RUNTIME_LATENCY_SECONDS,
)
from mlflow import MlflowClient

SEVERITY_WEIGHTS = {
    "low": 0.04,
    "medium": 0.08,
    "high": 0.14,
    "critical": 0.22,
}


@dataclass(slots=True)
class LoadedModel:
    model: Any
    metadata: ModelMetadata
    feature_names: list[str]


def build_reason_codes(features: dict[str, float], rule_hits: list[RuleHit]) -> list[ReasonCode]:
    codes = [
        ReasonCode(code=f"rule:{hit.rule_id}", description=hit.explanation, value=hit.score_delta)
        for hit in rule_hits
    ]
    heuristics = [
        (
            "velocity_spike",
            "Recent transaction velocity is elevated.",
            features.get("tx_count_5m", 0.0) >= 4,
        ),
        (
            "geo_jump",
            "Transaction location changed sharply.",
            features.get("geo_distance_from_last_tx_km", 0.0) >= 500.0,
        ),
        (
            "new_device",
            "Transaction originated from a new device.",
            features.get("device_new_for_account", 0.0) >= 1.0,
        ),
        (
            "amount_spike",
            "Amount is far above recent average.",
            features.get("amount_vs_recent_avg_ratio", 0.0) >= 3.0,
        ),
        (
            "high_risk_merchant",
            "Merchant is flagged as high risk.",
            features.get("high_risk_merchant_flag", 0.0) >= 1.0,
        ),
        (
            "auth_failures",
            "Recent authentication failures were observed.",
            features.get("failed_auth_count_recent", 0.0) >= 1.0,
        ),
    ]
    for code, description, matched in heuristics:
        if matched:
            codes.append(ReasonCode(code=code, description=description))
    unique: dict[str, ReasonCode] = {}
    for reason in codes:
        unique[reason.code] = reason
    return list(unique.values())[:8]


def combine_model_and_rules(
    probability: float,
    rule_hits: list[RuleHit],
    model_metadata: ModelMetadata,
) -> tuple[float, FraudDecision]:
    rule_weight = sum(SEVERITY_WEIGHTS[hit.severity] + hit.score_delta * 0.25 for hit in rule_hits)
    final_score = min(1.0, probability * 0.78 + min(rule_weight, 0.35))
    if (
        any(hit.severity == "critical" for hit in rule_hits)
        or final_score >= model_metadata.block_threshold
    ):
        return final_score, FraudDecision.BLOCK
    if final_score >= model_metadata.review_threshold or any(
        hit.severity == "high" for hit in rule_hits
    ):
        return final_score, FraudDecision.REVIEW
    return final_score, FraudDecision.APPROVE


class ModelRuntime:
    def __init__(self, settings: RuntimeSettings) -> None:
        self.settings = settings
        self._loaded_model: LoadedModel | None = None
        mlflow.set_tracking_uri(settings.mlflow_tracking_uri)

    def reload(self) -> LoadedModel:
        client = MlflowClient(tracking_uri=self.settings.mlflow_tracking_uri)
        version = client.get_model_version_by_alias(
            self.settings.mlflow_model_name,
            self.settings.mlflow_champion_alias,
        )
        model_uri = (
            f"models:/{self.settings.mlflow_model_name}@{self.settings.mlflow_champion_alias}"
        )
        sklearn_model = mlflow.sklearn.load_model(model_uri)
        metadata_path = mlflow.artifacts.download_artifacts(
            artifact_uri=f"runs:/{version.run_id}/model_metadata.json",
            dst_path=self.settings.model_local_cache_dir,
        )
        metadata_payload = json.loads(Path(metadata_path).read_text(encoding="utf-8"))
        feature_names = list(metadata_payload.pop("feature_names", MODEL_FEATURE_FIELDS))
        metadata = ModelMetadata.model_validate(metadata_payload)
        loaded = LoadedModel(
            model=sklearn_model,
            metadata=metadata,
            feature_names=feature_names,
        )
        self._loaded_model = loaded
        MODEL_INFO_GAUGE.labels(
            model_name=metadata.model_name,
            model_version=metadata.model_version,
            model_alias=metadata.model_alias,
        ).set(1)
        return loaded

    def ensure_loaded(self) -> LoadedModel:
        if self._loaded_model is None:
            return self.reload()
        return self._loaded_model

    def score(
        self, features: dict[str, float], rule_hits: list[RuleHit]
    ) -> tuple[float, float, FraudDecision, ModelMetadata, list[ReasonCode]]:
        loaded = self.ensure_loaded()
        frame = pd.DataFrame(
            [{name: float(features.get(name, 0.0)) for name in loaded.feature_names}]
        )
        with MODEL_RUNTIME_LATENCY_SECONDS.time():
            probability = float(loaded.model.predict_proba(frame)[0][1])
        final_score, decision = combine_model_and_rules(probability, rule_hits, loaded.metadata)
        MODEL_PREDICTION_COUNTER.labels(
            decision=decision, model_alias=loaded.metadata.model_alias
        ).inc()
        reasons = build_reason_codes(features, rule_hits)
        return probability, final_score, decision, loaded.metadata, reasons
