# Release Notes: v0.1.0

## Headline

ByteWatch Fraud Platform is now published as a full demo-ready real-time fraud operations project with a live analyst console, streaming decision pipeline, feedback persistence, model registry, and observability stack.

## Highlights

- End-to-end producer -> Kafka -> Bytewax -> Redis -> scoring -> PostgreSQL -> API -> analyst console flow
- Real analyst backlog with live polling-based updates and producer demo controls
- Hybrid decisioning with rules plus an XGBoost champion model
- MLflow model registry plus Evidently drift reporting
- Grafana and Prometheus for operator-facing observability
- Feedback loop persisted to PostgreSQL and published to `tx.feedback`

## What Is In This Release

- polished GitHub README with live screenshots and direct image wiring
- architecture, lifecycle, runbook, troubleshooting, and demo docs
- MIT license and improved repo hygiene
- CI expanded to cover Python quality, frontend test/build, and Compose sanity

## Validation Snapshot

- `docker compose config`
- `npm test` in `apps/analyst-console`
- `npm run build` in `apps/analyst-console`
- live local stack running with healthy service checks

## Honest Limitations

- analyst console live updates use short polling rather than SSE or websockets
- Grafana is linked as an operator surface and remains login-protected in the local demo stack
- local backend commands should run in Docker or Python 3.11; host Python 3.10 will fail on `datetime.UTC`

## Suggested GitHub Release Title

`v0.1.0 - live fraud platform release`

## Suggested GitHub Release Summary

Production-minded real-time fraud detection platform with Kafka ingestion, Bytewax stream processing, Redis online features, XGBoost plus rules hybrid scoring, FastAPI APIs, PostgreSQL persistence, a live Next.js analyst console, MLflow model registry, Evidently drift checks, and Grafana observability.

## Suggested Pinned Project Text

Built a real-time fraud ops platform with Kafka, Bytewax, Redis, XGBoost, FastAPI, PostgreSQL, MLflow, Evidently, Grafana, and a live analyst console for review workflows and feedback.
