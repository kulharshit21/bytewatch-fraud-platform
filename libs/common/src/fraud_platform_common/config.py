from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class RuntimeSettings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    service_name: str = "service"
    app_env: str = Field(default="local", alias="APP_ENV")
    app_version: str = Field(default="0.2.0", alias="APP_VERSION")
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")
    host: str = "0.0.0.0"
    port: int = 8000

    api_host: str = Field(default="0.0.0.0", alias="API_HOST")
    api_port: int = Field(default=8000, alias="API_PORT")
    producer_port: int = Field(default=8001, alias="PRODUCER_PORT")
    stream_worker_port: int = Field(default=8002, alias="STREAM_WORKER_PORT")
    trainer_port: int = Field(default=8003, alias="TRAINER_PORT")
    analyst_console_port: int = Field(default=3001, alias="ANALYST_CONSOLE_PORT")
    mlflow_port: int = Field(default=5000, alias="MLFLOW_PORT")

    kafka_bootstrap_servers: str = Field(default="localhost:9092", alias="KAFKA_BOOTSTRAP_SERVERS")
    kafka_external_bootstrap_servers: str = Field(
        default="localhost:29092",
        alias="KAFKA_EXTERNAL_BOOTSTRAP_SERVERS",
    )
    kafka_raw_topic: str = Field(default="tx.raw", alias="KAFKA_RAW_TOPIC")
    kafka_validated_topic: str = Field(default="tx.validated", alias="KAFKA_VALIDATED_TOPIC")
    kafka_enriched_topic: str = Field(default="tx.enriched", alias="KAFKA_ENRICHED_TOPIC")
    kafka_scored_topic: str = Field(default="tx.scored", alias="KAFKA_SCORED_TOPIC")
    kafka_decisions_topic: str = Field(default="tx.decisions", alias="KAFKA_DECISIONS_TOPIC")
    kafka_feedback_topic: str = Field(default="tx.feedback", alias="KAFKA_FEEDBACK_TOPIC")
    kafka_dlq_topic: str = Field(default="tx.dlq", alias="KAFKA_DLQ_TOPIC")

    database_url: str = Field(
        default="postgresql+psycopg://fraud:fraud@localhost:5432/fraud_platform",
        alias="DATABASE_URL",
    )
    redis_url: str = Field(default="redis://localhost:6379/0", alias="REDIS_URL")
    mlflow_tracking_uri: str = Field(default="http://localhost:5000", alias="MLFLOW_TRACKING_URI")
    mlflow_model_name: str = Field(default="fraud_xgboost", alias="MLFLOW_MODEL_NAME")
    mlflow_champion_alias: str = Field(default="champion", alias="MLFLOW_CHAMPION_ALIAS")
    mlflow_challenger_alias: str = Field(default="challenger", alias="MLFLOW_CHALLENGER_ALIAS")
    model_local_cache_dir: str = Field(
        default="/tmp/fraud-platform-model-cache",
        alias="MODEL_LOCAL_CACHE_DIR",
    )
    model_block_threshold: float = Field(default=0.82, alias="MODEL_BLOCK_THRESHOLD")
    model_review_threshold: float = Field(default=0.55, alias="MODEL_REVIEW_THRESHOLD")

    producer_autostart: bool = Field(default=False, alias="PRODUCER_AUTOSTART")
    producer_rate_per_second: float = Field(default=3.0, alias="PRODUCER_RATE_PER_SECOND")
    producer_max_events: int | None = Field(default=None, alias="PRODUCER_MAX_EVENTS")
    producer_fraud_ratio: float = Field(default=0.18, alias="PRODUCER_FRAUD_RATIO")
    producer_random_seed: int = Field(default=42, alias="PRODUCER_RANDOM_SEED")
    producer_export_path: str = Field(
        default="data/bootstrap_transactions.csv", alias="PRODUCER_EXPORT_PATH"
    )

    feature_window_1m_seconds: int = Field(default=60, alias="FEATURE_WINDOW_1M_SECONDS")
    feature_window_5m_seconds: int = Field(default=300, alias="FEATURE_WINDOW_5M_SECONDS")
    feature_window_1h_seconds: int = Field(default=3600, alias="FEATURE_WINDOW_1H_SECONDS")
    feature_profile_ttl_seconds: int = Field(default=2592000, alias="FEATURE_PROFILE_TTL_SECONDS")
    rules_config_path: str = Field(
        default="libs/rules/src/fraud_platform_rules/config/default_rules.yml",
        alias="RULES_CONFIG_PATH",
    )
    stream_autostart: bool = Field(default=False, alias="STREAM_AUTOSTART")

    api_public_base_url: str = Field(default="http://localhost:8000", alias="API_PUBLIC_BASE_URL")
    api_internal_base_url: str = Field(default="http://api:8000", alias="API_INTERNAL_BASE_URL")
    producer_internal_base_url: str = Field(
        default="http://localhost:8001",
        alias="PRODUCER_INTERNAL_BASE_URL",
    )
    stream_worker_internal_base_url: str = Field(
        default="http://localhost:8002",
        alias="STREAM_WORKER_INTERNAL_BASE_URL",
    )
    prometheus_url: str = Field(default="http://localhost:9090", alias="PROMETHEUS_URL")
    grafana_url: str = Field(default="http://localhost:3000", alias="GRAFANA_URL")

    data_dir: str = Field(default="data", alias="DATA_DIR")
    version: str = "0.2.0"

    @field_validator("producer_max_events", mode="before")
    @classmethod
    def blank_optional_ints_to_none(cls, value: object) -> object:
        if value in ("", None):
            return None
        return value
