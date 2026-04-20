# Runbook

## Bring up the full stack

```bash
docker compose up --build
```

This starts Kafka, Redis, PostgreSQL, Prometheus, Grafana, MLflow, migrations, model bootstrap, producer, stream worker, API, trainer, and analyst console.

## Clean bootstrap from empty state

Prefer this sequence when you need to prove the platform can recover from zero persisted state:

```bash
make reset-stack
make bootstrap
```

Equivalent Compose commands:

```bash
docker compose down --volumes --remove-orphans
docker compose up -d --build
```

## Key URLs

- Analyst console: `http://localhost:3001`
- API docs: `http://localhost:8000/docs`
- Producer status: `http://localhost:8001/producer/status`
- Worker status: `http://localhost:8002/worker/status`
- Trainer status: `http://localhost:8003/training/status`
- MLflow: `http://localhost:5000`
- Prometheus: `http://localhost:9090`
- Grafana: `http://localhost:3000`

## Useful operational commands

```bash
docker compose logs -f producer
docker compose logs -f stream-worker
docker compose logs -f api
docker compose logs -f trainer
make test-docker
make frontend-test
docker compose exec trainer fraud-trainer-cli bootstrap-model --force
docker compose exec trainer fraud-trainer-cli drift-report --sample-size 500
```

## Validate data is flowing

1. Open `http://localhost:8001/producer/status` and confirm `generated_events` is increasing.
2. Open `http://localhost:8002/worker/status` and confirm the worker is healthy.
3. Open `http://localhost:8000/dashboard/overview` and confirm totals increase.
4. Open `http://localhost:3001/cases` and confirm real cases appear.
5. Submit feedback on a real case, then run `POST /training/run?source=database` or `docker compose exec trainer fraud-trainer-cli bootstrap-model --force` to confirm retraining reads persisted analyst labels.

## Manual predict API

Use the producer export or API docs to post a `TransactionEvent` to `/predict`. The API persists the result and returns validated, enriched, scored, and decision payloads.

## Feedback-aware retraining

- `POST /cases/{case_id}/feedback` writes to `analyst_feedback` and publishes `tx.feedback`.
- `POST /training/run?source=database` reads `transactions_raw` plus the latest analyst feedback per transaction.
- When feedback exists, the trainer uses the analyst label instead of the synthetic `label` field from the raw event payload.

## Local alerting behavior

- Grafana alert rules are provisioned and evaluated locally.
- Grafana routes firing alerts to the API webhook sink at `POST /ops/grafana-alerts`.
- Verify alert health in the Grafana Alerting UI, the Grafana API, or the API logs for local webhook deliveries.
