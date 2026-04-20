# Trainer Service

Training and MLOps orchestration service shell for retraining, threshold evaluation, drift checks, and model registry integration.

## Local Run

```bash
uvicorn fraud_platform_trainer.main:app --reload --host 0.0.0.0 --port 8003
```

## Planned Responsibilities

- offline feature prep
- XGBoost training and evaluation
- MLflow registration and alias promotion
- Evidently drift report generation
