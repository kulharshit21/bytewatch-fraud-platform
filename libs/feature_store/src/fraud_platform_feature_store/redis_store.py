from __future__ import annotations

import time
from datetime import UTC, datetime, timedelta

from fraud_platform_common.config import RuntimeSettings
from fraud_platform_contracts import TransactionEvent
from fraud_platform_feature_engineering import FeatureContext, RecentTransaction
from fraud_platform_observability.metrics import REDIS_OPERATION_LATENCY_SECONDS
from redis import Redis

from fraud_platform_feature_store.base import FeatureStore


class RedisFeatureStore(FeatureStore):
    def __init__(self, settings: RuntimeSettings) -> None:
        self.settings = settings
        self.client = Redis.from_url(settings.redis_url, decode_responses=True)

    def claim_event(self, event_id: str) -> bool:
        started = time.perf_counter()
        claimed = bool(
            self.client.set(
                self._processed_key(event_id),
                "1",
                ex=self.settings.feature_profile_ttl_seconds,
                nx=True,
            )
        )
        REDIS_OPERATION_LATENCY_SECONDS.labels(operation="claim_event").observe(
            time.perf_counter() - started
        )
        return claimed

    def get_context(self, event: TransactionEvent) -> FeatureContext:
        started = time.perf_counter()
        account_key = event.account_id
        ts_ms = int(event.event_time.timestamp() * 1000)
        one_hour_ago_ms = int((event.event_time - timedelta(hours=1)).timestamp() * 1000)
        five_minutes_ago_ms = int((event.event_time - timedelta(minutes=5)).timestamp() * 1000)

        spend_rows = self.client.zrangebyscore(
            self._spend_key(account_key), min=one_hour_ago_ms, max=ts_ms
        )
        profile = self.client.hgetall(self._profile_key(account_key))
        merchant_count = int(
            self.client.get(self._merchant_count_key(account_key, event.merchant_id)) or 0
        )
        failed_auth_count = int(
            self.client.zcount(
                self._failed_auth_key(account_key), min=five_minutes_ago_ms, max=ts_ms
            )
        )
        is_known_device = bool(
            self.client.sismember(self._devices_key(account_key), event.device_id)
        )
        is_known_merchant = bool(
            self.client.sismember(self._merchants_key(account_key), event.merchant_id)
        )
        high_risk = bool(self.client.sismember("risk:merchants:high:set", event.merchant_id))
        if event.metadata.get("merchant_risk_level") == "high":
            high_risk = True

        txs = [self._decode_transaction_row(row) for row in spend_rows]
        context = FeatureContext(
            recent_transactions=txs,
            rolling_sum_30d=float(profile.get("rolling_sum_30d", 0.0)),
            rolling_count_30d=int(profile.get("rolling_count_30d", 0)),
            known_device=is_known_device,
            known_merchant=is_known_merchant,
            account_merchant_tx_count_30d=merchant_count,
            last_transaction_time=self._parse_dt(profile.get("last_transaction_time")),
            last_latitude=self._parse_float(profile.get("last_latitude")),
            last_longitude=self._parse_float(profile.get("last_longitude")),
            last_country=profile.get("last_country"),
            recent_failed_auth_count=failed_auth_count,
            high_risk_merchant=high_risk,
            first_seen=self._parse_dt(profile.get("first_seen")),
        )
        REDIS_OPERATION_LATENCY_SECONDS.labels(operation="get_context").observe(
            time.perf_counter() - started
        )
        return context

    def update_state(self, event: TransactionEvent) -> None:
        started = time.perf_counter()
        account_key = event.account_id
        ts_ms = int(event.event_time.timestamp() * 1000)
        tx_member = f"{ts_ms}|{event.event_id}"
        spend_member = f"{ts_ms}|{event.amount:.6f}|{event.event_id}"
        pipe = self.client.pipeline()
        pipe.zadd(self._tx_key(account_key), {tx_member: ts_ms})
        pipe.expire(self._tx_key(account_key), self.settings.feature_profile_ttl_seconds)
        pipe.zadd(self._spend_key(account_key), {spend_member: ts_ms})
        pipe.expire(self._spend_key(account_key), self.settings.feature_profile_ttl_seconds)
        pipe.sadd(self._devices_key(account_key), event.device_id)
        pipe.expire(self._devices_key(account_key), self.settings.feature_profile_ttl_seconds)
        pipe.sadd(self._merchants_key(account_key), event.merchant_id)
        pipe.expire(self._merchants_key(account_key), self.settings.feature_profile_ttl_seconds)
        pipe.incr(self._merchant_count_key(account_key, event.merchant_id))
        pipe.expire(
            self._merchant_count_key(account_key, event.merchant_id),
            self.settings.feature_profile_ttl_seconds,
        )
        if event.prior_auth_failures > 0:
            pipe.zadd(self._failed_auth_key(account_key), {tx_member: ts_ms})
            pipe.expire(
                self._failed_auth_key(account_key), self.settings.feature_profile_ttl_seconds
            )
        if event.metadata.get("merchant_risk_level") == "high":
            pipe.sadd("risk:merchants:high:set", event.merchant_id)
        profile_updates = {
            "last_transaction_time": event.event_time.astimezone(UTC).isoformat(),
            "last_latitude": event.latitude,
            "last_longitude": event.longitude,
            "last_country": event.country,
        }
        pipe.hset(self._profile_key(account_key), mapping=profile_updates)
        pipe.hincrbyfloat(self._profile_key(account_key), "rolling_sum_30d", event.amount)
        pipe.hincrby(self._profile_key(account_key), "rolling_count_30d", 1)
        pipe.hsetnx(
            self._profile_key(account_key),
            "first_seen",
            event.event_time.astimezone(UTC).isoformat(),
        )
        pipe.expire(self._profile_key(account_key), self.settings.feature_profile_ttl_seconds)
        cutoff_1h_ms = int((event.event_time - timedelta(hours=1)).timestamp() * 1000)
        pipe.zremrangebyscore(self._tx_key(account_key), 0, cutoff_1h_ms)
        pipe.zremrangebyscore(self._spend_key(account_key), 0, cutoff_1h_ms)
        cutoff_5m_ms = int((event.event_time - timedelta(minutes=5)).timestamp() * 1000)
        pipe.zremrangebyscore(self._failed_auth_key(account_key), 0, cutoff_5m_ms)
        pipe.execute()
        REDIS_OPERATION_LATENCY_SECONDS.labels(operation="update_state").observe(
            time.perf_counter() - started
        )

    @staticmethod
    def _parse_dt(value: str | None) -> datetime | None:
        if not value:
            return None
        return datetime.fromisoformat(value)

    @staticmethod
    def _parse_float(value: str | None) -> float | None:
        if value is None:
            return None
        return float(value)

    @staticmethod
    def _decode_transaction_row(row: str) -> RecentTransaction:
        ts_ms_str, amount_str, _ = row.split("|", 2)
        return RecentTransaction(
            event_time=datetime.fromtimestamp(int(ts_ms_str) / 1000, tz=UTC),
            amount=float(amount_str),
        )

    @staticmethod
    def _processed_key(event_id: str) -> str:
        return f"event:processed:{event_id}"

    @staticmethod
    def _tx_key(account_id: str) -> str:
        return f"acct:{account_id}:tx:zset"

    @staticmethod
    def _spend_key(account_id: str) -> str:
        return f"acct:{account_id}:spend:zset"

    @staticmethod
    def _devices_key(account_id: str) -> str:
        return f"acct:{account_id}:devices:set"

    @staticmethod
    def _merchants_key(account_id: str) -> str:
        return f"acct:{account_id}:merchants:set"

    @staticmethod
    def _merchant_count_key(account_id: str, merchant_id: str) -> str:
        return f"acct:{account_id}:merchant:{merchant_id}:count"

    @staticmethod
    def _failed_auth_key(account_id: str) -> str:
        return f"acct:{account_id}:failed_auth:zset"

    @staticmethod
    def _profile_key(account_id: str) -> str:
        return f"acct:{account_id}:profile:hash"
