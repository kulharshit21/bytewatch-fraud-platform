PROJECT_NAME := fraud-platform

.PHONY: help up down reset-stack bootstrap logs build lint format test test-docker frontend-test migrate api producer stream-worker trainer frontend-dev bootstrap-model bootstrap-data

help:
	@echo "Available targets:"
	@echo "  up            Start the local platform"
	@echo "  bootstrap     Start the local platform in detached mode"
	@echo "  down          Stop containers and remove local volumes"
	@echo "  reset-stack   Remove containers, named volumes, and orphans for a clean bootstrap"
	@echo "  logs          Tail docker compose logs"
	@echo "  build         Build docker images"
	@echo "  lint          Run Ruff"
	@echo "  format        Apply Ruff formatting"
	@echo "  test          Run pytest"
	@echo "  test-docker   Run backend pytest in a Dockerized Python 3.11 environment"
	@echo "  frontend-test Run analyst console Vitest suite"
	@echo "  migrate       Apply Alembic migrations"
	@echo "  api           Run the API locally"
	@echo "  producer      Run the producer locally"
	@echo "  stream-worker Run the stream worker locally"
	@echo "  trainer       Run the trainer locally"
	@echo "  frontend-dev  Run the analyst console locally"
	@echo "  bootstrap-model Train and register a champion model"
	@echo "  bootstrap-data Export synthetic training data"

up:
	docker compose up --build

bootstrap:
	docker compose up -d --build

down:
	docker compose down -v

reset-stack:
	docker compose down --volumes --remove-orphans

logs:
	docker compose logs -f

build:
	docker compose build

lint:
	ruff check .

format:
	ruff format .

test:
	pytest

test-docker:
	docker compose run --rm --no-deps api sh -lc "pip install -e '.[dev]' >/dev/null && pytest"

frontend-test:
	cd apps/analyst-console && npm test

migrate:
	alembic upgrade head

api:
	uvicorn fraud_platform_api.main:app --reload --host 0.0.0.0 --port 8000

producer:
	uvicorn fraud_platform_producer.main:app --reload --host 0.0.0.0 --port 8001

stream-worker:
	uvicorn fraud_platform_stream_worker.main:app --reload --host 0.0.0.0 --port 8002

trainer:
	uvicorn fraud_platform_trainer.main:app --reload --host 0.0.0.0 --port 8003

frontend-dev:
	cd apps/analyst-console && npm run dev

bootstrap-model:
	fraud-trainer-cli bootstrap-model

bootstrap-data:
	fraud-producer-cli export-dataset --output data/bootstrap_transactions.csv --events 3000
