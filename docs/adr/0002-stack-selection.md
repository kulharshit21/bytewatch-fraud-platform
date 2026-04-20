# ADR 0002: Kafka + Bytewax + Redis + FastAPI + PostgreSQL

## Status

Accepted

## Context

The platform needs a Python-friendly real-time path that is credible in 2026, easy to explain in interviews, and practical for a local demo environment.

## Decision

- Kafka is the event backbone for decoupled ingestion and downstream replay.
- Bytewax is the default Python-native stateful stream processor for the online path.
- Redis is the online feature and hot-state store for rolling windows and novelty checks.
- FastAPI is the API/runtime surface because it is testable, typed, and easy to instrument.
- PostgreSQL is the durable system of record with declarative partitioning for high-volume event tables.
- Prometheus + Grafana provide metrics, dashboards, and alerting as code.
- MLflow and Evidently are reserved for the training, registry, and drift phases.

## Rejected Alternatives

- Legacy `robinhood/faust`: not selected due to maintenance risk.
- Spark in the online path: not selected because it adds operational weight without improving the v1 streaming story.
- Notebook-only workflows: not selected because they do not demonstrate production engineering.

## Consequences

- The platform emphasizes online fraud context and observability rather than offline-only modeling.
- The architecture remains interview-defensible and aligned with current ecosystem support.
- Future phases can add MLflow and Evidently without changing the core event-driven design.
