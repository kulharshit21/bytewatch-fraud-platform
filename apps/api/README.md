# API Service

FastAPI service for fraud scoring, case management, model metadata, health endpoints, and Prometheus metrics.

## Local Run

```bash
uvicorn fraud_platform_api.main:app --reload --host 0.0.0.0 --port 8000
```

## Planned Responsibilities

- synchronous `/predict` scoring
- case and transaction query APIs
- analyst feedback ingestion
- model reload/admin hooks
- readiness and metrics endpoints
