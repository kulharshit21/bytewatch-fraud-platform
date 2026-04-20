from __future__ import annotations

from uuid import uuid4

from fraud_platform_common.config import RuntimeSettings
from fraud_platform_contracts import AnalystFeedbackEvent, FeedbackLabel
from fraud_platform_persistence.base import Base
from fraud_platform_persistence.db import build_engine
from fraud_platform_persistence.repositories import FraudRepository
from fraud_platform_producer.generation import SyntheticTransactionGenerator


def test_training_frame_overrides_synthetic_label_with_latest_feedback(tmp_path) -> None:
    database_path = tmp_path / "training-frame.db"
    settings = RuntimeSettings(
        service_name="trainer-test",
        DATABASE_URL=f"sqlite+pysqlite:///{database_path}",
    )
    engine = build_engine(settings)
    Base.metadata.create_all(engine)
    repository = FraudRepository(settings)

    generator = SyntheticTransactionGenerator(seed=17, fraud_ratio=0.0)
    event = generator.generate().model_copy(update={"label": 0})
    repository.save_raw_transaction(event, source_topic="tx.raw")
    repository.add_feedback(
        AnalystFeedbackEvent(
            case_id=uuid4(),
            transaction_id=event.transaction_id,
            event_id=event.event_id,
            analyst_id="analyst_007",
            feedback_label=FeedbackLabel.FRAUD,
            notes="Confirmed fraud after review.",
        )
    )

    frame = repository.training_frame()

    assert len(frame) == 1
    assert frame[0]["label"] == 1
    assert frame[0]["label_source"] == "analyst_feedback"
    assert frame[0]["latest_feedback_label"] == "fraud"
    assert frame[0]["feedback_count"] == 1
    assert frame[0]["feedback_labels"] == ["fraud"]
