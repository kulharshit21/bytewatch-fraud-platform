# Transaction Lifecycle

```mermaid
sequenceDiagram
    participant Producer
    participant Kafka
    participant BytewaxWorker as Bytewax Worker
    participant Redis
    participant Postgres
    participant API
    participant AnalystConsole as Analyst Console
    participant Trainer
    participant MLflow

    Producer->>Kafka: Publish TransactionEvent to tx.raw
    Kafka->>BytewaxWorker: Consume tx.raw
    BytewaxWorker->>BytewaxWorker: Validate + normalize payload
    BytewaxWorker->>Kafka: Publish ValidatedTransactionEvent to tx.validated
    BytewaxWorker->>Redis: Read rolling account/device/merchant context
    BytewaxWorker->>BytewaxWorker: Compute online features
    BytewaxWorker->>Kafka: Publish EnrichedTransactionEvent to tx.enriched
    BytewaxWorker->>BytewaxWorker: Run rule engine + champion model runtime
    BytewaxWorker->>Kafka: Publish ScoredTransactionEvent to tx.scored
    BytewaxWorker->>Kafka: Publish DecisionEvent to tx.decisions
    BytewaxWorker->>Postgres: Persist raw, scored, and decision records
    AnalystConsole->>API: Request cases, transactions, models, analytics
    API->>Postgres: Read case and transaction data
    API-->>AnalystConsole: Real queue, case detail, model, and overview payloads
    AnalystConsole->>API: Submit analyst feedback
    API->>Postgres: Persist analyst_feedback + audit_logs
    API->>Kafka: Publish AnalystFeedbackEvent to tx.feedback
    Trainer->>Postgres: Build retraining dataset from transactions + feedback
    Trainer->>MLflow: Register model version and assign alias
```

## DLQ Behavior

- Schema failures are wrapped in `DeadLetterEvent` and written to `tx.dlq`.
- Processing failures during feature enrichment or scoring are also written to `tx.dlq`.
- DLQ volume is emitted as a Prometheus counter and surfaced in Grafana.

## Retraining Behavior

- The trainer can bootstrap a champion model from generated CSV data.
- It can also rebuild training data from persisted PostgreSQL transactions that include labels.
- Promotion remains controlled: alias assignment is explicit and lives in MLflow.
