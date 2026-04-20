from __future__ import annotations

from datetime import UTC
from math import asin, cos, radians, sin, sqrt

from fraud_platform_contracts import Channel, TransactionEvent
from fraud_platform_feature_engineering.models import FeatureContext, MODEL_FEATURE_FIELDS


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    earth_radius_km = 6371.0
    d_lat = radians(lat2 - lat1)
    d_lon = radians(lon2 - lon1)
    a = (
        sin(d_lat / 2) ** 2
        + cos(radians(lat1)) * cos(radians(lat2)) * sin(d_lon / 2) ** 2
    )
    return 2 * earth_radius_km * asin(sqrt(a))


def compute_feature_values(event: TransactionEvent, context: FeatureContext) -> dict[str, float]:
    timestamps = [item.event_time for item in context.recent_transactions]
    amounts = [item.amount for item in context.recent_transactions]
    event_ts = event.event_time.astimezone(UTC)

    count_1m = sum(1 for ts in timestamps if (event_ts - ts.astimezone(UTC)).total_seconds() <= 60)
    count_5m = sum(1 for ts in timestamps if (event_ts - ts.astimezone(UTC)).total_seconds() <= 300)
    count_1h = sum(1 for ts in timestamps if (event_ts - ts.astimezone(UTC)).total_seconds() <= 3600)
    spend_sum_1h = float(sum(amounts))
    recent_avg = (
        context.rolling_sum_30d / context.rolling_count_30d
        if context.rolling_count_30d
        else event.amount
    )
    amount_vs_recent_avg_ratio = event.amount / max(recent_avg, 1.0)

    if (
        context.last_latitude is not None
        and context.last_longitude is not None
        and context.last_transaction_time is not None
    ):
        geo_distance = haversine_km(
            context.last_latitude,
            context.last_longitude,
            event.latitude,
            event.longitude,
        )
        time_since_last = max(
            0.0,
            (event_ts - context.last_transaction_time.astimezone(UTC)).total_seconds(),
        )
    else:
        geo_distance = 0.0
        time_since_last = 86_400.0

    first_seen = context.first_seen.astimezone(UTC) if context.first_seen else event_ts
    account_age_days = max(0.0, (event_ts - first_seen).total_seconds() / 86_400.0)
    country_mismatch = float(bool(event.is_international and context.last_country and context.last_country != event.country))
    night_flag = float(bool(event_ts.hour < 6 or event_ts.hour >= 23))
    channel_flags = {
        "channel_ecommerce": 1.0 if event.channel == Channel.ECOMMERCE else 0.0,
        "channel_pos": 1.0 if event.channel == Channel.POS else 0.0,
        "channel_upi": 1.0 if event.channel == Channel.UPI else 0.0,
        "channel_wallet": 1.0 if event.channel == Channel.WALLET else 0.0,
        "channel_transfer": 1.0 if event.channel == Channel.TRANSFER else 0.0,
    }
    features: dict[str, float] = {
        "amount": float(event.amount),
        "prior_auth_failures": float(event.prior_auth_failures),
        "card_present": float(event.card_present),
        "is_international": float(event.is_international),
        "tx_count_1m": float(count_1m),
        "tx_count_5m": float(count_5m),
        "tx_count_1h": float(count_1h),
        "spend_sum_1h": spend_sum_1h,
        "spend_avg_30d_proxy": float(recent_avg),
        "amount_vs_recent_avg_ratio": float(amount_vs_recent_avg_ratio),
        "device_new_for_account": float(not context.known_device),
        "merchant_new_for_account": float(not context.known_merchant),
        "geo_distance_from_last_tx_km": float(geo_distance),
        "time_since_last_tx_sec": float(time_since_last),
        "failed_auth_count_recent": float(context.recent_failed_auth_count),
        "international_mismatch": country_mismatch,
        "night_tx_flag": night_flag,
        "high_risk_merchant_flag": float(context.high_risk_merchant),
        "account_age_days": float(account_age_days),
        "account_merchant_tx_count_30d": float(context.account_merchant_tx_count_30d),
    }
    features.update(channel_flags)
    return {field: float(features[field]) for field in MODEL_FEATURE_FIELDS}
