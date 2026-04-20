# ADR 0001: Monorepo Streaming Fraud Platform

## Status

Accepted

## Context

The project needs to showcase backend engineering, streaming, ML systems, observability, and product thinking in one portfolio-friendly codebase. The implementation must stay understandable in interviews and runnable on a laptop with Docker Compose.

## Decision

Use a monorepo with dedicated `apps/`, `libs/`, `infra/`, and `docs/` boundaries.

- `apps/` owns deployable services and the analyst UI
- `libs/` owns reusable domain logic, contracts, persistence, feature code, and model runtime
- `infra/` owns Docker, Kafka, Postgres, Prometheus, and Grafana configuration
- `docs/adr` records decisions that are likely interview discussion points

## Consequences

- We keep architecture legible and modular from day one.
- Shared contracts and runtime code can be reused across services without copy/paste.
- Docker Compose remains the primary local integration surface for v1.
- This structure intentionally avoids an early microservice explosion while leaving room to split services later.
