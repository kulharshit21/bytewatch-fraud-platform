from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from fraud_platform_contracts import RuleHit, Severity, TransactionEvent


@dataclass(slots=True)
class RuleDefinition:
    rule_id: str
    type: str
    severity: Severity
    score_delta: float
    explanation: str
    params: dict[str, Any]


class RuleEngine:
    def __init__(self, definitions: list[RuleDefinition]) -> None:
        self.definitions = definitions

    @classmethod
    def from_yaml(cls, path: str) -> "RuleEngine":
        payload = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
        definitions = [
            RuleDefinition(
                rule_id=item["rule_id"],
                type=item["type"],
                severity=Severity(item["severity"]),
                score_delta=float(item["score_delta"]),
                explanation=item["explanation"],
                params={
                    key: value
                    for key, value in item.items()
                    if key not in {"rule_id", "type", "severity", "score_delta", "explanation"}
                },
            )
            for item in payload["rules"]
        ]
        return cls(definitions)

    def evaluate(self, event: TransactionEvent, features: dict[str, float]) -> list[RuleHit]:
        hits: list[RuleHit] = []
        for definition in self.definitions:
            match, metadata = self._matches(definition, event, features)
            if match:
                hits.append(
                    RuleHit(
                        rule_id=definition.rule_id,
                        severity=definition.severity,
                        score_delta=definition.score_delta,
                        explanation=definition.explanation,
                        metadata=metadata,
                    )
                )
        return hits

    @staticmethod
    def _compare(value: float, op: str, threshold: float) -> bool:
        if op == "gte":
            return value >= threshold
        if op == "gt":
            return value > threshold
        if op == "lte":
            return value <= threshold
        if op == "lt":
            return value < threshold
        raise ValueError(f"Unsupported rule operation: {op}")

    def _matches(
        self,
        definition: RuleDefinition,
        event: TransactionEvent,
        features: dict[str, float],
    ) -> tuple[bool, dict[str, Any]]:
        params = definition.params
        if definition.type == "threshold":
            feature = params["feature"]
            value = float(features.get(feature, 0.0))
            matched = self._compare(value, params["op"], float(params["threshold"]))
            return matched, {"feature": feature, "value": value}

        if definition.type == "impossible_travel":
            distance = float(features.get("geo_distance_from_last_tx_km", 0.0))
            time_since_last = float(features.get("time_since_last_tx_sec", 0.0))
            matched = distance >= float(params["distance_km"]) and time_since_last <= float(
                params["max_time_since_last_tx_sec"]
            )
            return matched, {"distance_km": distance, "time_since_last_tx_sec": time_since_last}

        if definition.type == "card_testing":
            tx_count = float(features.get(params["tx_count_feature"], 0.0))
            amount = float(event.amount)
            matched = tx_count >= float(params["tx_count_threshold"]) and amount <= float(
                params["amount_threshold"]
            )
            return matched, {"tx_count": tx_count, "amount": amount}

        if definition.type == "high_amount_new_device":
            matched = bool(features.get("device_new_for_account", 0.0)) and float(event.amount) >= float(
                params["amount_threshold"]
            )
            return matched, {"amount": event.amount, "device_new": features.get("device_new_for_account", 0.0)}

        if definition.type == "geo_combo":
            matched = bool(features.get("international_mismatch", 0.0)) and bool(
                features.get("night_tx_flag", 0.0)
            )
            return matched, {
                "international_mismatch": features.get("international_mismatch", 0.0),
                "night_tx_flag": features.get("night_tx_flag", 0.0),
            }

        raise ValueError(f"Unsupported rule type: {definition.type}")
