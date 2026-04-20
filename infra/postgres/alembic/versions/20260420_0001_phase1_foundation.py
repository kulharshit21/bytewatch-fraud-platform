"""Phase 1 foundation schema."""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "20260420_0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE transactions_raw (
            id UUID NOT NULL,
            event_id UUID NOT NULL,
            transaction_id VARCHAR(64) NOT NULL,
            account_id VARCHAR(64) NOT NULL,
            customer_id VARCHAR(64) NOT NULL,
            merchant_id VARCHAR(64) NOT NULL,
            amount NUMERIC(14, 2) NOT NULL,
            currency VARCHAR(8) NOT NULL,
            channel VARCHAR(32) NOT NULL,
            scenario VARCHAR(64),
            payload JSONB NOT NULL DEFAULT '{}'::jsonb,
            event_time TIMESTAMPTZ NOT NULL,
            ingested_at TIMESTAMPTZ NOT NULL DEFAULT timezone('utc', now()),
            created_at TIMESTAMPTZ NOT NULL DEFAULT timezone('utc', now()),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT timezone('utc', now()),
            PRIMARY KEY (id, event_time)
        ) PARTITION BY RANGE (event_time);
        """
    )

    op.execute(
        """
        CREATE TABLE transactions_raw_default
        PARTITION OF transactions_raw DEFAULT;
        """
    )

    op.execute(
        """
        DO $$
        DECLARE
            start_month date := date_trunc('month', now())::date;
            next_month date := (date_trunc('month', now()) + interval '1 month')::date;
            after_next_month date := (date_trunc('month', now()) + interval '2 month')::date;
        BEGIN
            EXECUTE format(
                'CREATE TABLE IF NOT EXISTS transactions_raw_%s '
                'PARTITION OF transactions_raw FOR VALUES FROM (%L) TO (%L)',
                to_char(start_month, 'YYYYMM'),
                start_month,
                next_month
            );
            EXECUTE format(
                'CREATE TABLE IF NOT EXISTS transactions_raw_%s '
                'PARTITION OF transactions_raw FOR VALUES FROM (%L) TO (%L)',
                to_char(next_month, 'YYYYMM'),
                next_month,
                after_next_month
            );
        END $$;
        """
    )

    op.execute(
        """
        CREATE TABLE transactions_scored (
            id UUID NOT NULL,
            event_id UUID NOT NULL,
            transaction_id VARCHAR(64) NOT NULL,
            account_id VARCHAR(64) NOT NULL,
            merchant_id VARCHAR(64) NOT NULL,
            model_name VARCHAR(128) NOT NULL,
            model_version VARCHAR(128) NOT NULL,
            decision VARCHAR(32) NOT NULL,
            scenario VARCHAR(64),
            score DOUBLE PRECISION NOT NULL,
            threshold DOUBLE PRECISION NOT NULL,
            rule_hits JSONB NOT NULL DEFAULT '[]'::jsonb,
            features JSONB NOT NULL DEFAULT '{}'::jsonb,
            reason_codes JSONB NOT NULL DEFAULT '[]'::jsonb,
            event_time TIMESTAMPTZ NOT NULL,
            created_at TIMESTAMPTZ NOT NULL DEFAULT timezone('utc', now()),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT timezone('utc', now()),
            PRIMARY KEY (id, event_time)
        ) PARTITION BY RANGE (event_time);
        """
    )

    op.execute(
        """
        CREATE TABLE transactions_scored_default
        PARTITION OF transactions_scored DEFAULT;
        """
    )

    op.execute(
        """
        DO $$
        DECLARE
            start_month date := date_trunc('month', now())::date;
            next_month date := (date_trunc('month', now()) + interval '1 month')::date;
            after_next_month date := (date_trunc('month', now()) + interval '2 month')::date;
        BEGIN
            EXECUTE format(
                'CREATE TABLE IF NOT EXISTS transactions_scored_%s '
                'PARTITION OF transactions_scored FOR VALUES FROM (%L) TO (%L)',
                to_char(start_month, 'YYYYMM'),
                start_month,
                next_month
            );
            EXECUTE format(
                'CREATE TABLE IF NOT EXISTS transactions_scored_%s '
                'PARTITION OF transactions_scored FOR VALUES FROM (%L) TO (%L)',
                to_char(next_month, 'YYYYMM'),
                next_month,
                after_next_month
            );
        END $$;
        """
    )

    op.create_table(
        "fraud_decisions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("transaction_id", sa.String(length=64), nullable=False),
        sa.Column("scored_transaction_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("decision", sa.String(length=32), nullable=False),
        sa.Column("source", sa.String(length=32), nullable=False),
        sa.Column("case_status", sa.String(length=32), nullable=False),
        sa.Column("model_metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("rule_hits", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("decision_time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_fraud_decisions_transaction_id", "fraud_decisions", ["transaction_id"])
    op.create_index("ix_fraud_decisions_decision", "fraud_decisions", ["decision"])

    op.create_table(
        "analyst_feedback",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("case_id", sa.String(length=64), nullable=False),
        sa.Column("transaction_id", sa.String(length=64), nullable=False),
        sa.Column("analyst_id", sa.String(length=64), nullable=False),
        sa.Column("feedback_label", sa.String(length=32), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_analyst_feedback_case_id", "analyst_feedback", ["case_id"])
    op.create_index("ix_analyst_feedback_feedback_label", "analyst_feedback", ["feedback_label"])

    op.create_table(
        "model_registry_cache",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("model_name", sa.String(length=128), nullable=False),
        sa.Column("model_version", sa.String(length=128), nullable=False),
        sa.Column("alias", sa.String(length=64), nullable=True),
        sa.Column("run_id", sa.String(length=64), nullable=True),
        sa.Column("stage", sa.String(length=64), nullable=True),
        sa.Column("metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_model_registry_cache_alias", "model_registry_cache", ["alias"])
    op.create_index(
        "ix_model_registry_cache_model_version", "model_registry_cache", ["model_version"]
    )

    op.create_table(
        "audit_logs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("entity_type", sa.String(length=64), nullable=False),
        sa.Column("entity_id", sa.String(length=128), nullable=False),
        sa.Column("action", sa.String(length=64), nullable=False),
        sa.Column("actor", sa.String(length=64), nullable=False),
        sa.Column("payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_audit_logs_entity_type", "audit_logs", ["entity_type"])
    op.create_index("ix_audit_logs_entity_id", "audit_logs", ["entity_id"])

    op.execute("CREATE INDEX ix_transactions_raw_event_time ON transactions_raw (event_time)")
    op.execute("CREATE INDEX ix_transactions_raw_account_id ON transactions_raw (account_id)")
    op.execute("CREATE INDEX ix_transactions_raw_merchant_id ON transactions_raw (merchant_id)")
    op.execute("CREATE INDEX ix_transactions_scored_event_time ON transactions_scored (event_time)")
    op.execute("CREATE INDEX ix_transactions_scored_decision ON transactions_scored (decision)")
    op.execute(
        "CREATE INDEX ix_transactions_scored_model_version ON transactions_scored (model_version)"
    )


def downgrade() -> None:
    op.drop_index("ix_transactions_scored_model_version", table_name="transactions_scored")
    op.drop_index("ix_transactions_scored_decision", table_name="transactions_scored")
    op.drop_index("ix_transactions_scored_event_time", table_name="transactions_scored")
    op.drop_index("ix_transactions_raw_merchant_id", table_name="transactions_raw")
    op.drop_index("ix_transactions_raw_account_id", table_name="transactions_raw")
    op.drop_index("ix_transactions_raw_event_time", table_name="transactions_raw")
    op.drop_index("ix_audit_logs_entity_id", table_name="audit_logs")
    op.drop_index("ix_audit_logs_entity_type", table_name="audit_logs")
    op.drop_table("audit_logs")
    op.drop_index("ix_model_registry_cache_model_version", table_name="model_registry_cache")
    op.drop_index("ix_model_registry_cache_alias", table_name="model_registry_cache")
    op.drop_table("model_registry_cache")
    op.drop_index("ix_analyst_feedback_feedback_label", table_name="analyst_feedback")
    op.drop_index("ix_analyst_feedback_case_id", table_name="analyst_feedback")
    op.drop_table("analyst_feedback")
    op.drop_index("ix_fraud_decisions_decision", table_name="fraud_decisions")
    op.drop_index("ix_fraud_decisions_transaction_id", table_name="fraud_decisions")
    op.drop_table("fraud_decisions")
    op.execute("DROP TABLE IF EXISTS transactions_scored_default")
    op.execute(
        """
        DO $$
        DECLARE
            part record;
        BEGIN
            FOR part IN
                SELECT inhrelid::regclass AS partition_name
                FROM pg_inherits
                WHERE inhparent = 'transactions_scored'::regclass
            LOOP
                EXECUTE format('DROP TABLE IF EXISTS %s CASCADE', part.partition_name);
            END LOOP;
        END $$;
        """
    )
    op.execute("DROP TABLE IF EXISTS transactions_scored CASCADE")
    op.execute("DROP TABLE IF EXISTS transactions_raw_default")
    op.execute(
        """
        DO $$
        DECLARE
            part record;
        BEGIN
            FOR part IN
                SELECT inhrelid::regclass AS partition_name
                FROM pg_inherits
                WHERE inhparent = 'transactions_raw'::regclass
            LOOP
                EXECUTE format('DROP TABLE IF EXISTS %s CASCADE', part.partition_name);
            END LOOP;
        END $$;
        """
    )
    op.execute("DROP TABLE IF EXISTS transactions_raw CASCADE")
