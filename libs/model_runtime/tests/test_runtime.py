from fraud_platform_contracts import ModelMetadata, RuleHit, Severity
from fraud_platform_model_runtime import build_reason_codes, combine_model_and_rules


def test_combine_model_and_rules_blocks_on_critical_rule() -> None:
    metadata = ModelMetadata(
        model_name="fraud_xgboost",
        model_version="1",
        model_alias="champion",
        review_threshold=0.55,
        block_threshold=0.82,
    )
    hits = [
        RuleHit(
            rule_id="impossible_travel",
            severity=Severity.CRITICAL,
            score_delta=0.32,
            explanation="Location changed too quickly.",
        )
    ]
    final_score, decision = combine_model_and_rules(0.41, hits, metadata)
    assert final_score > 0.41
    assert decision == "BLOCK"


def test_reason_codes_capture_rule_and_feature_signals() -> None:
    hits = [
        RuleHit(
            rule_id="very_high_velocity",
            severity=Severity.HIGH,
            score_delta=0.2,
            explanation="Velocity threshold breached.",
        )
    ]
    reasons = build_reason_codes(
        {
            "tx_count_5m": 7.0,
            "geo_distance_from_last_tx_km": 800.0,
            "device_new_for_account": 1.0,
            "amount_vs_recent_avg_ratio": 4.2,
            "high_risk_merchant_flag": 1.0,
            "failed_auth_count_recent": 2.0,
        },
        hits,
    )
    codes = {reason.code for reason in reasons}
    assert "rule:very_high_velocity" in codes
    assert "geo_jump" in codes
    assert "new_device" in codes
