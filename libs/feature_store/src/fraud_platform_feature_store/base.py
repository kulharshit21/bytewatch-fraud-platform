from __future__ import annotations

from abc import ABC, abstractmethod

from fraud_platform_contracts import TransactionEvent
from fraud_platform_feature_engineering import FeatureContext


class FeatureStore(ABC):
    @abstractmethod
    def claim_event(self, event_id: str) -> bool:
        raise NotImplementedError

    @abstractmethod
    def get_context(self, event: TransactionEvent) -> FeatureContext:
        raise NotImplementedError

    @abstractmethod
    def update_state(self, event: TransactionEvent) -> None:
        raise NotImplementedError
