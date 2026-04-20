from __future__ import annotations

import hashlib
import random
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Iterable
from uuid import uuid4

import pandas as pd
from faker import Faker

from fraud_platform_contracts import (
    Channel,
    PaymentMethod,
    SimulationScenario,
    TransactionEvent,
)


faker = Faker()


CITY_PROFILES = [
    {"country": "IN", "city": "Mumbai", "latitude": 19.0760, "longitude": 72.8777},
    {"country": "IN", "city": "Bengaluru", "latitude": 12.9716, "longitude": 77.5946},
    {"country": "IN", "city": "Delhi", "latitude": 28.6139, "longitude": 77.2090},
    {"country": "IN", "city": "Hyderabad", "latitude": 17.3850, "longitude": 78.4867},
    {"country": "IN", "city": "Chennai", "latitude": 13.0827, "longitude": 80.2707},
    {"country": "SG", "city": "Singapore", "latitude": 1.3521, "longitude": 103.8198},
    {"country": "AE", "city": "Dubai", "latitude": 25.2048, "longitude": 55.2708},
]

MERCHANTS = [
    {"merchant_id": "m_electro_1", "category": "electronics", "risk_level": "medium"},
    {"merchant_id": "m_grocery_1", "category": "grocery", "risk_level": "low"},
    {"merchant_id": "m_fashion_1", "category": "fashion", "risk_level": "low"},
    {"merchant_id": "m_travel_1", "category": "travel", "risk_level": "medium"},
    {"merchant_id": "m_wallet_1", "category": "wallet_topup", "risk_level": "medium"},
    {"merchant_id": "m_crypto_1", "category": "digital_goods", "risk_level": "high"},
    {"merchant_id": "m_gambling_1", "category": "gaming", "risk_level": "high"},
]


@dataclass(slots=True)
class AccountProfile:
    account_id: str
    customer_id: str
    payment_instrument_id: str
    email_hash: str
    phone_hash: str
    base_amount: float
    home_city: dict[str, object]
    payment_method: PaymentMethod
    known_devices: list[str]
    trusted_merchants: list[dict[str, str]]
    last_event_time: datetime = field(default_factory=lambda: datetime.now(UTC))
    last_city: dict[str, object] | None = None


class SyntheticPopulation:
    def __init__(self, seed: int = 42, account_count: int = 250) -> None:
        self.random = random.Random(seed)
        self._accounts = [self._build_account(index) for index in range(account_count)]

    @property
    def accounts(self) -> list[AccountProfile]:
        return self._accounts

    def _build_account(self, index: int) -> AccountProfile:
        home_city = self.random.choice(CITY_PROFILES[:5])
        payment_method = self.random.choice(
            [
                PaymentMethod.CREDIT_CARD,
                PaymentMethod.DEBIT_CARD,
                PaymentMethod.UPI,
                PaymentMethod.WALLET,
            ]
        )
        account_id = f"acct_{index:05d}"
        customer_id = f"cust_{index:05d}"
        email_hash = hashlib.sha256(f"{customer_id}@example.com".encode("utf-8")).hexdigest()[:16]
        phone_hash = hashlib.sha256(f"+91-90000{index:05d}".encode("utf-8")).hexdigest()[:16]
        devices = [f"device_{index:05d}_{slot}" for slot in range(1, self.random.randint(2, 4))]
        trusted_merchants = self.random.sample(MERCHANTS[:5], k=2)
        return AccountProfile(
            account_id=account_id,
            customer_id=customer_id,
            payment_instrument_id=f"pi_{index:05d}",
            email_hash=email_hash,
            phone_hash=phone_hash,
            base_amount=round(self.random.uniform(200.0, 1500.0), 2),
            home_city=home_city,
            payment_method=payment_method,
            known_devices=devices,
            trusted_merchants=trusted_merchants,
            last_city=home_city,
        )


class SyntheticTransactionGenerator:
    def __init__(self, seed: int = 42, fraud_ratio: float = 0.18, account_count: int = 250) -> None:
        self.random = random.Random(seed)
        self.population = SyntheticPopulation(seed=seed, account_count=account_count)
        self.fraud_ratio = fraud_ratio
        self.sequence = 0
        self._scenario_weights = {
            SimulationScenario.NORMAL_BEHAVIOR: max(0.01, 1.0 - fraud_ratio),
            SimulationScenario.VELOCITY_BURST: fraud_ratio * 0.18,
            SimulationScenario.IMPOSSIBLE_TRAVEL: fraud_ratio * 0.16,
            SimulationScenario.CARD_TESTING: fraud_ratio * 0.18,
            SimulationScenario.ACCOUNT_TAKEOVER: fraud_ratio * 0.16,
            SimulationScenario.NEW_DEVICE_HIGH_AMOUNT: fraud_ratio * 0.16,
            SimulationScenario.RISKY_MERCHANT: fraud_ratio * 0.16,
        }

    def generate(self, *, now: datetime | None = None, scenario: SimulationScenario | None = None) -> TransactionEvent:
        account = self.random.choice(self.population.accounts)
        chosen_scenario = scenario or self._pick_scenario()
        event_time = now or self._next_event_time(account)
        event = self._render_event(account, event_time, chosen_scenario)
        account.last_event_time = event.event_time
        account.last_city = {
            "country": event.country,
            "city": event.city,
            "latitude": event.latitude,
            "longitude": event.longitude,
        }
        if event.device_id not in account.known_devices:
            account.known_devices.append(event.device_id)
        if all(merchant["merchant_id"] != event.merchant_id for merchant in account.trusted_merchants):
            account.trusted_merchants.append(
                {
                    "merchant_id": event.merchant_id,
                    "category": event.merchant_category,
                    "risk_level": event.metadata.get("merchant_risk_level", "low"),
                }
            )
        return event

    def export_dataset(self, output_path: str, events: int) -> str:
        start_time = datetime.now(UTC) - timedelta(days=30)
        rows = []
        for index in range(events):
            event_time = start_time + timedelta(seconds=index * 45)
            event = self.generate(now=event_time)
            rows.append(event.model_dump(mode="json"))
        output = Path(output_path)
        output.parent.mkdir(parents=True, exist_ok=True)
        pd.DataFrame(rows).to_csv(output, index=False)
        return str(output)

    def iter_events(self, count: int, *, start_time: datetime | None = None) -> Iterable[TransactionEvent]:
        base = start_time or datetime.now(UTC)
        for offset in range(count):
            yield self.generate(now=base + timedelta(seconds=offset * 5))

    def _pick_scenario(self) -> SimulationScenario:
        scenarios = list(self._scenario_weights.keys())
        weights = list(self._scenario_weights.values())
        return self.random.choices(scenarios, weights=weights, k=1)[0]

    def _next_event_time(self, account: AccountProfile) -> datetime:
        return account.last_event_time + timedelta(seconds=self.random.randint(5, 45))

    def _render_event(
        self,
        account: AccountProfile,
        event_time: datetime,
        scenario: SimulationScenario,
    ) -> TransactionEvent:
        self.sequence += 1
        merchant, city, device_id, amount, auth_failures, label, channel = self._scenario_payload(
            account,
            scenario,
        )
        event_id = uuid4()
        user_agent_hash = hashlib.sha256(f"{account.account_id}:{device_id}".encode("utf-8")).hexdigest()[:16]
        ip_address = self._ip_for_country(str(city["country"]))
        is_international = city["country"] != account.home_city["country"]
        return TransactionEvent(
            event_id=event_id,
            event_time=event_time,
            account_id=account.account_id,
            customer_id=account.customer_id,
            transaction_id=f"txn_{self.sequence:08d}",
            payment_instrument_id=account.payment_instrument_id,
            merchant_id=str(merchant["merchant_id"]),
            merchant_category=str(merchant["category"]),
            amount=round(amount, 2),
            currency="INR" if city["country"] == "IN" else "USD",
            country=str(city["country"]),
            city=str(city["city"]),
            latitude=float(city["latitude"]),
            longitude=float(city["longitude"]),
            channel=channel,
            device_id=device_id,
            ip_address=ip_address,
            user_agent_hash=user_agent_hash,
            email_hash=account.email_hash,
            phone_hash=account.phone_hash,
            prior_auth_failures=auth_failures,
            payment_method=account.payment_method,
            card_present=channel == Channel.POS,
            is_international=is_international,
            label=label,
            simulation_scenario=scenario,
            metadata={
                "merchant_risk_level": merchant["risk_level"],
                "home_country": account.home_city["country"],
                "home_city": account.home_city["city"],
            },
        )

    def _scenario_payload(
        self,
        account: AccountProfile,
        scenario: SimulationScenario,
    ) -> tuple[dict[str, str], dict[str, object], str, float, int, int, Channel]:
        if scenario == SimulationScenario.NORMAL_BEHAVIOR:
            merchant = self.random.choice(account.trusted_merchants)
            city = account.last_city or account.home_city
            device = self.random.choice(account.known_devices)
            amount = max(25.0, self.random.gauss(account.base_amount, account.base_amount * 0.25))
            return merchant, city, device, amount, 0, 0, self._channel_for_account(account)

        if scenario == SimulationScenario.VELOCITY_BURST:
            merchant = self.random.choice(account.trusted_merchants)
            city = account.home_city
            device = self.random.choice(account.known_devices)
            amount = max(50.0, self.random.gauss(account.base_amount * 0.75, account.base_amount * 0.15))
            return merchant, city, device, amount, self.random.randint(0, 1), 1, Channel.ECOMMERCE

        if scenario == SimulationScenario.IMPOSSIBLE_TRAVEL:
            merchant = self.random.choice(MERCHANTS)
            far_city = self.random.choice(CITY_PROFILES[5:])
            device = f"{account.account_id}_device_travel_{self.sequence}"
            amount = max(300.0, self.random.gauss(account.base_amount * 1.4, account.base_amount * 0.3))
            return merchant, far_city, device, amount, self.random.randint(1, 2), 1, Channel.ECOMMERCE

        if scenario == SimulationScenario.CARD_TESTING:
            merchant = self.random.choice(MERCHANTS)
            city = account.home_city
            device = self.random.choice(account.known_devices)
            amount = round(self.random.uniform(1.0, 15.0), 2)
            return merchant, city, device, amount, self.random.randint(1, 4), 1, Channel.ECOMMERCE

        if scenario == SimulationScenario.ACCOUNT_TAKEOVER:
            merchant = self.random.choice(MERCHANTS)
            city = self.random.choice(CITY_PROFILES)
            device = f"{account.account_id}_compromised_{self.sequence}"
            amount = max(400.0, self.random.gauss(account.base_amount * 2.0, account.base_amount * 0.4))
            return merchant, city, device, amount, self.random.randint(3, 6), 1, Channel.TRANSFER

        if scenario == SimulationScenario.NEW_DEVICE_HIGH_AMOUNT:
            merchant = self.random.choice(account.trusted_merchants)
            city = account.home_city
            device = f"{account.account_id}_fresh_{self.sequence}"
            amount = max(1_500.0, self.random.gauss(account.base_amount * 3.2, account.base_amount * 0.5))
            return merchant, city, device, amount, self.random.randint(1, 2), 1, Channel.ECOMMERCE

        merchant = self.random.choice([item for item in MERCHANTS if item["risk_level"] == "high"])
        city = self.random.choice(CITY_PROFILES[5:])
        device = f"{account.account_id}_risk_{self.sequence}"
        amount = max(600.0, self.random.gauss(account.base_amount * 1.6, account.base_amount * 0.35))
        return merchant, city, device, amount, self.random.randint(1, 3), 1, Channel.WALLET

    def _channel_for_account(self, account: AccountProfile) -> Channel:
        if account.payment_method == PaymentMethod.UPI:
            return Channel.UPI
        if account.payment_method == PaymentMethod.WALLET:
            return Channel.WALLET
        return self.random.choice([Channel.POS, Channel.ECOMMERCE])

    def _ip_for_country(self, country_code: str) -> str:
        octets = {
            "IN": "49",
            "SG": "103",
            "AE": "94",
        }
        prefix = octets.get(country_code, "203")
        return f"{prefix}.{self.random.randint(0, 255)}.{self.random.randint(0, 255)}.{self.random.randint(1, 254)}"
