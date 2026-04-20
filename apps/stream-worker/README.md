# Stream Worker

Streaming service shell for the Bytewax topology that will validate, enrich, score, and route transaction events.

## Local Run

```bash
uvicorn fraud_platform_stream_worker.main:app --reload --host 0.0.0.0 --port 8002
```

## Planned Responsibilities

- consume `tx.raw`
- write rolling state to Redis
- emit `tx.validated`, `tx.enriched`, `tx.scored`, and `tx.decisions`
- route malformed events to `tx.dlq`
