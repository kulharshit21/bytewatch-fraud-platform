# Troubleshooting

## API says no champion model found

- Check `http://localhost:8003/training/status`.
- If no model is registered, run:

```bash
docker compose exec trainer fraud-trainer-cli bootstrap-model --force
```

## The stack looks stale or polluted by previous data

- Reset all named volumes and restart from zero state:

```bash
make reset-stack
make bootstrap
```

- If you prefer raw Compose commands:

```bash
docker compose down --volumes --remove-orphans
docker compose up -d --build
```

## Analyst console loads but shows empty states

- Empty states are real, not fake placeholders.
- Confirm the producer is running and generating events:

```bash
curl http://localhost:8001/producer/status
```

- Confirm the worker is healthy:

```bash
curl http://localhost:8002/worker/status
```

## Live mode looks frozen

- Confirm the live mode toggle on `Overview` or `Cases` is enabled.
- Confirm the live endpoints are responding:

```bash
curl http://localhost:8000/dashboard/live
curl "http://localhost:8000/cases/live?status=open&decision=REVIEW"
```

- If the producer was paused during a demo, resume it from the Overview demo controls or with:

```bash
curl -X POST http://localhost:8000/demo/producer/start
```

- Remember that `Models` and individual case detail pages are still snapshot-oriented; the live polling emphasis is on `Overview` and `Cases`.

## Stream worker is unhealthy

- Check Redis, Kafka, PostgreSQL, and MLflow health in `docker compose ps`.
- Review logs:

```bash
docker compose logs -f stream-worker
```

## Tests fail locally on Python 3.10

- This repo intentionally targets Python 3.11.
- Use Docker or a local Python 3.11 interpreter for backend test execution.
- Reproducible commands:

```bash
make test-docker
make frontend-test
```

## Grafana panels are empty

- Confirm Prometheus is scraping the service metrics endpoints.
- Open Prometheus and query one of the metrics directly, for example:

```text
fraud_platform_worker_events_total
```

## Grafana alerts are healthy but no notifications arrive

- In the local stack, Grafana sends alerts to the API webhook sink at `POST /ops/grafana-alerts`.
- If you do not see deliveries, inspect both Grafana and API logs:

```bash
docker compose logs -f grafana
docker compose logs -f api
```

- The local stack does not send email notifications.

## Drift dashboard stays flat

- Drift gauges only update after the trainer generates a fresh Evidently report:

```bash
docker compose exec trainer fraud-trainer-cli drift-report --sample-size 500
```

## Feedback was submitted but you want to confirm retraining sees it

- Verify the feedback row exists in PostgreSQL:

```bash
docker compose exec postgres psql -U fraud -d fraud_platform -c "select transaction_id, feedback_label, created_at from analyst_feedback order by created_at desc limit 5;"
```

- Verify the trainer database frame applies the latest analyst label:

```bash
docker compose exec trainer python -c "from fraud_platform_common.config import RuntimeSettings; from fraud_platform_persistence import FraudRepository; repo = FraudRepository(RuntimeSettings(service_name='trainer')); rows = [row for row in repo.training_frame() if row['feedback_count'] > 0]; print(rows[-1]['transaction_id'], rows[-1]['label_source'], rows[-1]['latest_feedback_label'], rows[-1]['label'])"
```

## Demo controls do not create obvious changes

- Use one of the burst endpoints instead of waiting for the normal fraud ratio:

```bash
curl -X POST http://localhost:8000/demo/producer/burst -H "content-type: application/json" -d "{\"scenario\":\"impossible_travel\",\"count\":10}"
curl -X POST http://localhost:8000/demo/producer/burst -H "content-type: application/json" -d "{\"scenario\":\"new_device_high_amount\",\"count\":12}"
```

- The `Overview` page shows burst impact fastest through the activity feed and recent window counters.
- The `Cases` page is best for showing new backlog rows arriving automatically.
