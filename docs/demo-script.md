# 5-Minute Demo Script

## 1. Show the architecture

- Open the root README and briefly explain the producer → Kafka → Bytewax → Redis → scoring → Postgres → API → analyst console loop.

## 2. Show the live stack

- Open:
  - `http://localhost:3001/overview`
  - `http://localhost:3001/cases`
  - `http://localhost:3000`
  - `http://localhost:5000`
- Point out that `Overview` and `Cases` start with live mode already enabled.

## 3. Show producer and worker activity

- Visit:
  - `http://localhost:8001/producer/status`
  - `http://localhost:8002/worker/status`

## 4. Show the wow moment

- On `http://localhost:3001/overview`, point to:
  - live mode toggle
  - last updated label
  - live activity feed
  - demo controls
- Click one real control:
  - `Inject impossible travel burst`
  - or `Inject new-device high-amount burst`
- Wait 5–10 seconds and show:
  - activity feed updates
  - recent window counters move
  - `http://localhost:3001/cases` advances without a manual reload

## 5. Show analyst workflow

- Open `http://localhost:3001/cases`
- Mention that the page now defaults to the real analyst backlog: `decision=REVIEW` and `status=open`
- Open a case detail page
- Submit feedback
- Show the feedback timeline updated from persisted data
- Mention that the same feedback is stored in `analyst_feedback`, published to `tx.feedback`, and used by `POST /training/run?source=database` as the latest label for retraining

## 6. Show model lifecycle

- Visit `http://localhost:3001/models`
- Explain champion alias, MLflow registration, thresholds, stored metrics, and that database retraining now respects analyst feedback labels

## 7. Show monitoring

- Open `http://localhost:3001/monitoring` first and explain the three layers:
  - readiness
  - DB-backed business counts
  - Grafana/Prometheus observability
- Then open Grafana dashboards and point out throughput, DLQ, worker latency, model runtime latency, and drift score panels
- In Grafana Alerting, show that local alert rules are provisioned and evaluating, and mention that local notifications are routed to the API webhook sink instead of email
