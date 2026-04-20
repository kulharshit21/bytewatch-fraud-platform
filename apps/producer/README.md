# Producer Service

Synthetic transaction producer service that will generate realistic payment activity and fraud scenarios for local demos, offline exports, and Kafka ingestion.

## Local Run

```bash
uvicorn fraud_platform_producer.main:app --reload --host 0.0.0.0 --port 8001
```

## Planned Responsibilities

- scenario-driven event generation
- Kafka publish mode
- CSV / JSONL dataset export
- seeded reproducibility controls
