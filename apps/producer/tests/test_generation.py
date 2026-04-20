from fraud_platform_contracts import SimulationScenario
from fraud_platform_producer.generation import SyntheticTransactionGenerator


def test_generator_produces_realistic_transaction_shape() -> None:
    generator = SyntheticTransactionGenerator(seed=7, fraud_ratio=0.2)
    event = generator.generate()
    assert event.account_id.startswith("acct_")
    assert event.transaction_id.startswith("txn_")
    assert event.amount > 0
    assert event.country
    assert event.metadata["merchant_risk_level"] in {"low", "medium", "high"}


def test_generator_can_force_specific_scenario() -> None:
    generator = SyntheticTransactionGenerator(seed=11, fraud_ratio=0.2)
    event = generator.generate(scenario=SimulationScenario.ACCOUNT_TAKEOVER)
    assert event.simulation_scenario == SimulationScenario.ACCOUNT_TAKEOVER
    assert event.label == 1
