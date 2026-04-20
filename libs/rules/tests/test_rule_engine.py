from fraud_platform_common.config import RuntimeSettings
from fraud_platform_contracts import Channel, PaymentMethod, SimulationScenario, TransactionEvent
from fraud_platform_rules import RuleEngine


def build_event(**overrides: object) -> TransactionEvent:
    payload = {
        "account_id": "acct_1",
        "customer_id": "cust_1",
        "transaction_id": "txn_1",
        "payment_instrument_id": "pi_1",
        "merchant_id": "merchant_1",
        "merchant_category": "electronics",
        "amount": 25.0,
        "currency": "INR",
        "country": "IN",
        "city": "Mumbai",
        "latitude": 19.076,
        "longitude": 72.8777,
        "channel": Channel.ECOMMERCE,
        "device_id": "device_1",
        "ip_address": "203.0.113.1",
        "user_agent_hash": "ua_hash",
        "email_hash": "email_hash",
        "phone_hash": "phone_hash",
        "payment_method": PaymentMethod.CREDIT_CARD,
        "card_present": False,
        "is_international": False,
        "simulation_scenario": SimulationScenario.CARD_TESTING,
    }
    payload.update(overrides)
    return TransactionEvent(**payload)


def test_rule_engine_fires_card_testing_rule() -> None:
    settings = RuntimeSettings()
    engine = RuleEngine.from_yaml(settings.rules_config_path)
    features = {
        "geo_distance_from_last_tx_km": 0.0,
        "time_since_last_tx_sec": 20.0,
        "tx_count_5m": 5.0,
        "device_new_for_account": 0.0,
        "high_risk_merchant_flag": 0.0,
        "international_mismatch": 0.0,
        "night_tx_flag": 0.0,
    }
    hits = engine.evaluate(build_event(amount=9.0), features)
    assert any(hit.rule_id == "repeated_small_amount_card_testing" for hit in hits)


def test_rule_engine_fires_impossible_travel_rule() -> None:
    settings = RuntimeSettings()
    engine = RuleEngine.from_yaml(settings.rules_config_path)
    features = {
        "geo_distance_from_last_tx_km": 1700.0,
        "time_since_last_tx_sec": 900.0,
        "tx_count_5m": 1.0,
        "device_new_for_account": 0.0,
        "high_risk_merchant_flag": 0.0,
        "international_mismatch": 1.0,
        "night_tx_flag": 1.0,
    }
    hits = engine.evaluate(build_event(amount=500.0), features)
    assert any(hit.rule_id == "impossible_travel" for hit in hits)
