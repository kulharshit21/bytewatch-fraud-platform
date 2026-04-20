from __future__ import annotations

import numpy as np

from fraud_platform_common.config import RuntimeSettings
from fraud_platform_producer.generation import SyntheticTransactionGenerator
from fraud_platform_trainer.training import FraudTrainer


def test_build_feature_frame_generates_model_features():
    trainer = FraudTrainer(RuntimeSettings(service_name="trainer"))
    generator = SyntheticTransactionGenerator(seed=11, fraud_ratio=0.3)
    events = list(generator.iter_events(40))

    frame = trainer._build_feature_frame(events)  # noqa: SLF001

    assert not frame.empty
    assert "tx_count_5m" in frame.columns
    assert "label" in frame.columns
    assert frame["label"].isin([0, 1]).all()


def test_threshold_sweep_returns_review_and_block_levels():
    result = FraudTrainer._threshold_sweep(  # noqa: SLF001
        y_true=np.array([0, 0, 1, 1, 1]),
        probabilities=np.array([0.1, 0.2, 0.7, 0.88, 0.95]),
    )

    assert 0.1 <= result["best_f1_threshold"] <= 0.95
    assert result["high_precision_threshold"] >= result["best_f1_threshold"]
