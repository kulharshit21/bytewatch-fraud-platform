# Real-Time Fraud Detection Platform

Production-minded fraud platform built as a modular monorepo with Kafka ingestion, a Bytewax stream worker, Redis online features, XGBoost + rules hybrid scoring, FastAPI business APIs, PostgreSQL persistence, MLflow model registry, Evidently drift reporting, Grafana dashboards, and a real Next.js analyst console.

## What Is Real Now

- Kafka topics are bootstrapped automatically for `tx.raw`, `tx.validated`, `tx.enriched`, `tx.scored`, `tx.decisions`, `tx.feedback`, and `tx.dlq`.
- The producer generates realistic synthetic transaction behavior and publishes directly to `tx.raw`.
- The stream worker consumes Kafka with Bytewax, validates events, computes Redis-backed online features, scores with rules + model runtime, persists to PostgreSQL, and emits downstream topics.
- The trainer can bootstrap a champion XGBoost model, register it in MLflow, and generate Evidently drift artifacts.
- The API exposes real fraud workflows: `/predict`, `/cases`, `/cases/{id}`, feedback submission, model metadata, analytics, and dashboard payloads.
- The analyst console reads live API data. There are no hardcoded queue rows or fake case cards left in the UI.
- Grafana dashboards and alert rules are provisioned from files and target real metrics emitted by the services.
- Database retraining now consumes analyst feedback from `analyst_feedback` by overriding synthetic labels with the latest analyst decision when available.

## Architecture

```mermaid
flowchart LR
    Producer[Producer\nsynthetic tx generator] -->|tx.raw| Kafka[(Kafka)]
    Kafka --> Worker[Bytewax stream worker]
    Worker -->|tx.validated / tx.enriched / tx.scored / tx.decisions| Kafka
    Worker --> Redis[(Redis online feature store)]
    Worker --> Postgres[(PostgreSQL)]
    API[FastAPI business API] --> Postgres
    API --> Redis
    API --> Kafka
    Trainer[Trainer / ML Ops] --> MLflow[(MLflow)]
    Trainer --> Evidently[Evidently reports]
    Trainer --> Postgres
    Analyst[Next.js analyst console] --> API
    Prometheus[(Prometheus)] --> Grafana[(Grafana)]
    API --> Prometheus
    Producer --> Prometheus
    Worker --> Prometheus
    Trainer --> Prometheus
```

More detail:

- [Architecture overview](docs/architecture/overview.md)
- [Transaction lifecycle](docs/architecture/transaction-lifecycle.md)
- [Runbook](docs/runbook.md)
- [Troubleshooting](docs/troubleshooting.md)
- [Demo script](docs/demo-script.md)

## Repository Layout

```text
apps/
  analyst-console/    # Next.js internal operations UI
  api/                # FastAPI business API
  producer/           # synthetic traffic generator + export CLI
  stream-worker/      # Bytewax flow + stream runtime
  trainer/            # XGBoost training, MLflow, Evidently
libs/
  common/             # config, logging, FastAPI service helpers
  contracts/          # shared Pydantic event contracts
  feature_engineering/# online/offline feature computation
  feature_store/      # Redis + in-memory feature store adapters
  model_runtime/      # champion model loading and hybrid scoring
  observability/      # Prometheus metrics
  persistence/        # SQLAlchemy models and repositories
  rules/              # YAML-driven fraud rules
infra/
  docker/             # Dockerfiles
  grafana/            # dashboards + alerts as code
  kafka/              # topic bootstrap
  postgres/           # init SQL + Alembic migrations
  prometheus/
docs/
tests/
```

## Core Runtime Flow

1. The producer emits realistic transaction events to `tx.raw`.
2. Bytewax consumes `tx.raw`.
3. The worker validates payloads and normalizes fields.
4. Redis provides hot account/device/merchant context for rolling features.
5. The rule engine + champion XGBoost model produce a final score and decision.
6. The worker persists raw, scored, and decision records to PostgreSQL.
7. FastAPI exposes cases, transactions, model metadata, analytics, and feedback endpoints.
8. The analyst console renders overview, queue, case detail, models, and monitoring pages from the real API.
9. Analyst feedback is written to PostgreSQL, published to `tx.feedback`, and stored for retraining.
10. The trainer can retrain and refresh MLflow + Evidently artifacts from generated CSV data or persisted database rows, with analyst feedback taking precedence over synthetic labels.

## Quickstart

### Prerequisites

- Docker Desktop / Docker Engine with Compose
- Node 20+ only if you want to run the analyst console outside Docker
- Python 3.11 for local non-Docker backend development

### One-command local stack

```bash
docker compose up --build
```

The stack now includes:

- `kafka`
- `redis`
- `postgres`
- `prometheus`
- `grafana`
- `mlflow`
- `db-migrate`
- `model-bootstrap`
- `producer`
- `stream-worker`
- `api`
- `trainer`
- `analyst-console`

### Clean bootstrap from empty state

Use this when you want a deterministic local reset instead of reusing old Kafka, Redis, PostgreSQL, MLflow, or Grafana state.

```bash
make reset-stack
make bootstrap
```

Equivalent Docker Compose sequence:

```bash
docker compose down --volumes --remove-orphans
docker compose up -d --build
```

### Local URLs

- Analyst console: `http://localhost:3001`
- API docs: `http://localhost:8000/docs`
- Producer: `http://localhost:8001/producer/status`
- Stream worker: `http://localhost:8002/worker/status`
- Trainer: `http://localhost:8003/training/status`
- Grafana: `http://localhost:3000`
- Prometheus: `http://localhost:9090`
- MLflow: `http://localhost:5000`

## Useful Commands

```bash
docker compose up --build
make reset-stack
make bootstrap
docker compose logs -f stream-worker
docker compose logs -f api
docker compose exec trainer fraud-trainer-cli bootstrap-model --force
docker compose exec trainer python -c "from fraud_platform_common.config import RuntimeSettings; from fraud_platform_persistence import FraudRepository; repo = FraudRepository(RuntimeSettings(service_name='trainer')); rows = repo.training_frame(); print(rows[-1]['label_source'], rows[-1]['latest_feedback_label'])"
docker compose exec trainer fraud-trainer-cli drift-report --sample-size 500
docker compose exec producer fraud-producer-cli export-dataset --output /data/bootstrap_transactions.csv --events 3000
docker compose exec api python -c "import requests; print(requests.get('http://localhost:8000/dashboard/overview').json())"
make test-docker
make frontend-test
```

## Local Development

### Python

```bash
python -m compileall apps libs
pytest
```

Important: this repo targets Python 3.11. Running tests with Python 3.10 will fail because the code intentionally uses Python 3.11 features such as `StrEnum` and `datetime.UTC`.

Reproducible backend test run from Docker:

```bash
make test-docker
```

### Analyst console

```bash
cd apps/analyst-console
npm install
npm run build
npm test
```

## Testing Status

Automated coverage now includes:

- contract schema tests
- synthetic producer tests
- in-memory feature store tests
- rule engine tests
- model runtime tests
- stream processor behavior tests
- trainer feature-frame and threshold tests
- API business endpoint tests
- repository feedback-to-training frame tests
- analyst console render/API helper/server-action tests

Recommended verification commands:

```bash
make test-docker
make frontend-test
```

## Observability

- Prometheus metrics are exposed by every Python service on `/metrics`.
- Grafana dashboards are provisioned from `infra/grafana/dashboards`.
- Alert rules are provisioned from `infra/grafana/provisioning/alerting`.
- Local development routes firing alerts to the API webhook sink at `/ops/grafana-alerts` instead of external email or chat systems.
- Drift gauges are updated from trainer-side Evidently report generation.

## Known Limitations

- The worker runtime runs Bytewax inside the service process for local simplicity; distributed deployment tuning is still out of scope for this repo.
- The current MLflow service uses a local SQLite-backed metadata store suitable for local demos, not HA production.
- Feedback-driven retraining is implemented as a controlled/manual workflow, not automatic promotion.
- Local Grafana notifications terminate at the API webhook sink rather than a real on-call channel.
- Kafka lag monitoring is not fully instrumented yet.
- The current host shell used during implementation only had Python 3.10 available, so backend runtime verification here stopped at syntax/static validation; use Docker or Python 3.11 locally for full execution.

## Why This Project Is Defensible

- real streaming path instead of notebook-only fraud scoring
- Redis online features rather than fake precomputed aggregates
- hybrid rules + model decisioning with persisted explanation artifacts
- analyst feedback loop with DB persistence and Kafka event emission
- model registry and drift reporting included in the same repo
- dashboards, alerts, migrations, health checks, and service boundaries are version-controlled
