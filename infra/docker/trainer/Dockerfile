FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /workspace

RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential curl \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml README.md alembic.ini ./
COPY apps ./apps
COPY libs ./libs
COPY infra/postgres ./infra/postgres

RUN pip install --upgrade pip \
    && pip install -e ".[api,runtime,trainer,producer]"

CMD ["uvicorn", "fraud_platform_trainer.main:app", "--host", "0.0.0.0", "--port", "8003"]
