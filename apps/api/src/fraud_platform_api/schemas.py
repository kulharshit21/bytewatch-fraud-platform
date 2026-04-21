from __future__ import annotations

from fraud_platform_contracts import FeedbackLabel, SimulationScenario, TransactionEvent
from pydantic import BaseModel, Field


class PredictRequest(TransactionEvent):
    pass


class FeedbackRequest(BaseModel):
    analyst_id: str = Field(min_length=2)
    feedback_label: FeedbackLabel
    notes: str | None = None


class ProducerBurstRequest(BaseModel):
    scenario: SimulationScenario
    count: int = Field(default=12, ge=1, le=100)


class ProducerBoostRequest(BaseModel):
    fraud_ratio: float = Field(default=0.6, ge=0.01, le=0.95)
    rate_per_second: float | None = Field(default=6.0, ge=0.1, le=25.0)
    duration_seconds: int = Field(default=30, ge=5, le=300)
