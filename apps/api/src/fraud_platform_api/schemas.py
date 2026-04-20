from __future__ import annotations

from pydantic import BaseModel, Field

from fraud_platform_contracts import FeedbackLabel, TransactionEvent


class PredictRequest(TransactionEvent):
    pass


class FeedbackRequest(BaseModel):
    analyst_id: str = Field(min_length=2)
    feedback_label: FeedbackLabel
    notes: str | None = None
