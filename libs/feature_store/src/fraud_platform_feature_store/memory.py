from __future__ import annotations

from collections import defaultdict, deque
from datetime import timedelta
from uuid import UUID

from fraud_platform_contracts import TransactionEvent
from fraud_platform_feature_engineering import FeatureContext, RecentTransaction

from fraud_platform_feature_store.base import FeatureStore


class MemoryFeatureStore(FeatureStore):
    def __init__(self) -> None:
        self._processed: set[str] = set()
        self._transactions: dict[str, deque[RecentTransaction]] = defaultdict(deque)
        self._devices: dict[str, set[str]] = defaultdict(set)
        self._merchants: dict[str, set[str]] = defaultdict(set)
        self._merchant_counts: dict[tuple[str, str], int] = defaultdict(int)
        self._failed_auths: dict[str, deque] = defaultdict(deque)
        self._profiles: dict[str, dict[str, object]] = defaultdict(dict)
        self._high_risk_merchants: set[str] = set()

    def claim_event(self, event_id: str | UUID) -> bool:
        event_key = str(event_id)
        if event_key in self._processed:
            return False
        self._processed.add(event_key)
        return True

    def get_context(self, event: TransactionEvent) -> FeatureContext:
        txs = self._transactions[event.account_id]
        failed = self._failed_auths[event.account_id]
        now = event.event_time
        one_hour_ago = now - timedelta(hours=1)
        five_minutes_ago = now - timedelta(minutes=5)
        while txs and txs[0].event_time < one_hour_ago:
            txs.popleft()
        while failed and failed[0] < five_minutes_ago:
            failed.popleft()

        profile = self._profiles[event.account_id]
        return FeatureContext(
            recent_transactions=list(txs),
            rolling_sum_30d=float(profile.get("rolling_sum_30d", 0.0)),
            rolling_count_30d=int(profile.get("rolling_count_30d", 0)),
            known_device=event.device_id in self._devices[event.account_id],
            known_merchant=event.merchant_id in self._merchants[event.account_id],
            account_merchant_tx_count_30d=self._merchant_counts[
                (event.account_id, event.merchant_id)
            ],
            last_transaction_time=profile.get("last_transaction_time"),  # type: ignore[arg-type]
            last_latitude=profile.get("last_latitude"),  # type: ignore[arg-type]
            last_longitude=profile.get("last_longitude"),  # type: ignore[arg-type]
            last_country=profile.get("last_country"),  # type: ignore[arg-type]
            recent_failed_auth_count=len(failed),
            high_risk_merchant=(
                event.merchant_id in self._high_risk_merchants
                or event.metadata.get("merchant_risk_level") == "high"
            ),
            first_seen=profile.get("first_seen"),  # type: ignore[arg-type]
        )

    def update_state(self, event: TransactionEvent) -> None:
        self._transactions[event.account_id].append(
            RecentTransaction(event_time=event.event_time, amount=event.amount)
        )
        self._devices[event.account_id].add(event.device_id)
        self._merchants[event.account_id].add(event.merchant_id)
        self._merchant_counts[(event.account_id, event.merchant_id)] += 1
        if event.prior_auth_failures > 0:
            self._failed_auths[event.account_id].append(event.event_time)
        if event.metadata.get("merchant_risk_level") == "high":
            self._high_risk_merchants.add(event.merchant_id)

        profile = self._profiles[event.account_id]
        profile["rolling_sum_30d"] = float(profile.get("rolling_sum_30d", 0.0)) + event.amount
        profile["rolling_count_30d"] = int(profile.get("rolling_count_30d", 0)) + 1
        profile["last_transaction_time"] = event.event_time
        profile["last_latitude"] = event.latitude
        profile["last_longitude"] = event.longitude
        profile["last_country"] = event.country
        profile.setdefault("first_seen", event.event_time)
