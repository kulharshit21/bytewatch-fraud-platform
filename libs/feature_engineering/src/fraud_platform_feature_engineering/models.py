from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime


MODEL_FEATURE_FIELDS = [
    "amount",
    "prior_auth_failures",
    "card_present",
    "is_international",
    "tx_count_1m",
    "tx_count_5m",
    "tx_count_1h",
    "spend_sum_1h",
    "spend_avg_30d_proxy",
    "amount_vs_recent_avg_ratio",
    "device_new_for_account",
    "merchant_new_for_account",
    "geo_distance_from_last_tx_km",
    "time_since_last_tx_sec",
    "failed_auth_count_recent",
    "international_mismatch",
    "night_tx_flag",
    "high_risk_merchant_flag",
    "account_age_days",
    "account_merchant_tx_count_30d",
    "channel_ecommerce",
    "channel_pos",
    "channel_upi",
    "channel_wallet",
    "channel_transfer",
]


@dataclass(slots=True)
class RecentTransaction:
    event_time: datetime
    amount: float


@dataclass(slots=True)
class FeatureContext:
    recent_transactions: list[RecentTransaction] = field(default_factory=list)
    rolling_sum_30d: float = 0.0
    rolling_count_30d: int = 0
    known_device: bool = False
    known_merchant: bool = False
    account_merchant_tx_count_30d: int = 0
    last_transaction_time: datetime | None = None
    last_latitude: float | None = None
    last_longitude: float | None = None
    last_country: str | None = None
    recent_failed_auth_count: int = 0
    high_risk_merchant: bool = False
    first_seen: datetime | None = None
