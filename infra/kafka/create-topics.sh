#!/usr/bin/env bash
set -euo pipefail

BOOTSTRAP_SERVER="${KAFKA_BOOTSTRAP_SERVERS:-kafka:9092}"

create_topic() {
  local topic="$1"
  local partitions="$2"
  local replication_factor="$3"

  /opt/kafka/bin/kafka-topics.sh \
    --bootstrap-server "${BOOTSTRAP_SERVER}" \
    --create \
    --if-not-exists \
    --topic "${topic}" \
    --partitions "${partitions}" \
    --replication-factor "${replication_factor}"
}

create_topic "tx.raw" 6 1
create_topic "tx.validated" 6 1
create_topic "tx.enriched" 6 1
create_topic "tx.scored" 6 1
create_topic "tx.decisions" 6 1
create_topic "tx.feedback" 3 1
create_topic "tx.dlq" 3 1
create_topic "system.metrics" 1 1

echo "Kafka topics created successfully."
