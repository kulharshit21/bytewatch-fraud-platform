from datetime import UTC, datetime, timedelta

from fraud_platform_contracts import Channel, PaymentMethod, SimulationScenario, TransactionEvent
from fraud_platform_feature_engineering import compute_feature_values
from fraud_platform_feature_store import MemoryFeatureStore


def build_event(**overrides: object) -> TransactionEvent:
    base_time = datetime(2026, 4, 20, 12, 0, tzinfo=UTC)
    payload = {
        "account_id": "acct_1",
        "customer_id": "cust_1",
        "transaction_id": f"txn_{overrides.get('transaction_id', '1')}",
        "payment_instrument_id": "pi_1",
        "merchant_id": "merch_1",
        "merchant_category": "electronics",
        "amount": 100.0,
        "currency": "INR",
        "country": "IN",
        "city": "Mumbai",
        "latitude": 19.076,
        "longitude": 72.8777,
        "channel": Channel.ECOMMERCE,
        "device_id": "device_1",
        "ip_address": "203.0.113.10",
        "user_agent_hash": "ua_hash",
        "email_hash": "email_hash",
        "phone_hash": "phone_hash",
        "payment_method": PaymentMethod.CREDIT_CARD,
        "card_present": False,
        "is_international": False,
        "simulation_scenario": SimulationScenario.NORMAL_BEHAVIOR,
        "event_time": base_time,
    }
    payload.update(overrides)
    return TransactionEvent(**payload)


def test_memory_feature_store_tracks_novelty_and_velocity() -> None:
    store = MemoryFeatureStore()
    first = build_event()
    assert store.claim_event(str(first.event_id))
    context = store.get_context(first)
    features = compute_feature_values(first, context)
    assert features["device_new_for_account"] == 1.0
    store.update_state(first)

    second = build_event(
        transaction_id="2",
        event_time=first.event_time + timedelta(seconds=30),
        amount=250.0,
    )
    second_context = store.get_context(second)
    second_features = compute_feature_values(second, second_context)
    assert second_features["tx_count_1m"] >= 1.0
    assert second_features["device_new_for_account"] == 0.0
    assert second_features["amount_vs_recent_avg_ratio"] > 1.0


def test_memory_feature_store_detects_geo_jump() -> None:
    store = MemoryFeatureStore()
    first = build_event(latitude=12.9716, longitude=77.5946, city="Bengaluru")
    store.claim_event(str(first.event_id))
    store.update_state(first)

    second = build_event(
        transaction_id="3",
        city="Delhi",
        country="IN",
        latitude=28.6139,
        longitude=77.2090,
        event_time=first.event_time + timedelta(minutes=5),
    )
    features = compute_feature_values(second, store.get_context(second))
    assert features["geo_distance_from_last_tx_km"] > 1000.0
