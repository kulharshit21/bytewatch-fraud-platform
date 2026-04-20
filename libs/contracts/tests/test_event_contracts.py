from fraud_platform_contracts import (
    Channel,
    DecisionEvent,
    FeedbackLabel,
    FraudDecision,
    ModelMetadata,
    PaymentMethod,
    SimulationScenario,
    TransactionEvent,
    dump_json,
    load_json,
)


def build_transaction() -> TransactionEvent:
    return TransactionEvent(
        account_id="acct_1",
        customer_id="cust_1",
        transaction_id="txn_1",
        payment_instrument_id="pi_1",
        merchant_id="merch_1",
        merchant_category="grocery",
        amount=125.5,
        currency="INR",
        country="IN",
        city="Bengaluru",
        latitude=12.9716,
        longitude=77.5946,
        channel=Channel.ECOMMERCE,
        device_id="device_1",
        ip_address="203.0.113.10",
        user_agent_hash="ua_hash",
        email_hash="email_hash",
        phone_hash="phone_hash",
        payment_method=PaymentMethod.CREDIT_CARD,
        card_present=False,
        is_international=False,
        simulation_scenario=SimulationScenario.NORMAL_BEHAVIOR,
    )


def test_transaction_event_round_trip() -> None:
    event = build_transaction()
    payload = dump_json(event)
    restored = load_json(TransactionEvent, payload)
    assert restored.event_id == event.event_id
    assert restored.amount == event.amount
    assert restored.simulation_scenario == event.simulation_scenario


def test_decision_event_schema_is_stable() -> None:
    model_metadata = ModelMetadata(
        model_name="fraud_xgboost",
        model_version="1",
        model_alias="champion",
        review_threshold=0.55,
        block_threshold=0.82,
    )
    transaction = build_transaction()
    decision = DecisionEvent(
        event_id=transaction.event_id,
        transaction_id=transaction.transaction_id,
        account_id=transaction.account_id,
        decision=FraudDecision.REVIEW,
        final_score=0.72,
        model_probability=0.68,
        model_metadata=model_metadata,
        simulation_scenario=transaction.simulation_scenario,
    )
    dumped = decision.model_dump()
    assert dumped["decision"] == FraudDecision.REVIEW
    assert dumped["model_metadata"]["model_alias"] == "champion"


def test_feedback_label_values_are_serializable() -> None:
    assert FeedbackLabel.FRAUD == "fraud"
