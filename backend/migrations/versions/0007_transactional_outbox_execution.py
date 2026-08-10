"""Add canonical outbox events and fenced internal execution records.

Revision ID: 0007_outbox_execution
Revises: 0006_pg_audit_immutable
Create Date: 2026-08-10
"""

import sqlalchemy as sa
from alembic import op

revision = "0007_outbox_execution"
down_revision = "0006_pg_audit_immutable"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "outbox_events",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("event_type", sa.String(80), nullable=False),
        sa.Column("schema_version", sa.Integer(), nullable=False),
        sa.Column("aggregate_type", sa.String(80), nullable=False),
        sa.Column("aggregate_id", sa.String(64), nullable=False),
        sa.Column("aggregate_version", sa.Integer(), nullable=False),
        sa.Column("owner_user_id", sa.String(64), nullable=False),
        sa.Column("controller_id", sa.String(64), nullable=False),
        sa.Column("data_subject_id", sa.String(64), nullable=False),
        sa.Column("actor_id", sa.String(64), nullable=False),
        sa.Column("on_behalf_of_id", sa.String(64), nullable=True),
        sa.Column("sensitivity", sa.String(32), nullable=False),
        sa.Column("correlation_id", sa.String(64), nullable=False),
        sa.Column("causation_id", sa.String(128), nullable=False),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("capability_mode", sa.String(64), nullable=False),
        sa.Column("producer_key", sa.String(128), nullable=False),
        sa.Column("payload_json", sa.Text(), nullable=False),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("available_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("attempt_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("max_attempts", sa.Integer(), nullable=False, server_default="3"),
        sa.Column("cycle", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("lease_owner", sa.String(64), nullable=True),
        sa.Column("lease_token", sa.String(64), nullable=True),
        sa.Column("lease_expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_failure_code", sa.String(64), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("delivered_at", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint("producer_key", name="uq_outbox_event_producer_key"),
        sa.CheckConstraint("schema_version = 1", name="ck_outbox_schema_version"),
        sa.CheckConstraint("aggregate_version >= 0", name="ck_outbox_aggregate_version"),
        sa.CheckConstraint(
            "sensitivity IN ('public', 'household_shared', 'personal', 'financial', "
            "'health', 'identity', 'legal')",
            name="ck_outbox_sensitivity",
        ),
        sa.CheckConstraint(
            "capability_mode = 'local-mock-synthetic'",
            name="ck_outbox_capability_mode",
        ),
        sa.CheckConstraint(
            "event_type IN ('intent.captured.v1', 'intent.clarification_requested.v1', "
            "'commitment.created.v1', 'schedule.no_feasible_proposal.v1', "
            "'schedule.proposed.v1', 'schedule.approved.v1', "
            "'schedule.rejected.v1', 'schedule.changed.v1', 'command.denied.v1')",
            name="ck_outbox_event_type",
        ),
        sa.CheckConstraint(
            "status IN ('pending', 'processing', 'retry', 'delivered', 'failed')",
            name="ck_outbox_status",
        ),
        sa.CheckConstraint(
            "attempt_count >= 0 AND attempt_count <= max_attempts "
            "AND max_attempts BETWEEN 1 AND 10",
            name="ck_outbox_attempt_budget",
        ),
        sa.CheckConstraint("cycle >= 0", name="ck_outbox_cycle"),
        sa.CheckConstraint("length(payload_json) <= 2048", name="ck_outbox_payload_size"),
        sa.CheckConstraint(
            "(status = 'processing' AND lease_owner IS NOT NULL "
            "AND lease_token IS NOT NULL AND lease_expires_at IS NOT NULL) OR "
            "(status <> 'processing' AND lease_owner IS NULL "
            "AND lease_token IS NULL AND lease_expires_at IS NULL)",
            name="ck_outbox_lease_state",
        ),
        sa.CheckConstraint(
            "(status IN ('retry', 'failed') AND last_failure_code IS NOT NULL) OR "
            "(status NOT IN ('retry', 'failed') AND last_failure_code IS NULL)",
            name="ck_outbox_failure_state",
        ),
        sa.CheckConstraint(
            "(status = 'delivered' AND delivered_at IS NOT NULL) OR "
            "(status <> 'delivered' AND delivered_at IS NULL)",
            name="ck_outbox_delivery_state",
        ),
    )
    op.create_index("ix_outbox_events_event_type", "outbox_events", ["event_type"])
    op.create_index("ix_outbox_events_aggregate_id", "outbox_events", ["aggregate_id"])
    op.create_index("ix_outbox_events_owner_user_id", "outbox_events", ["owner_user_id"])
    op.create_index("ix_outbox_events_correlation_id", "outbox_events", ["correlation_id"])
    op.create_index("ix_outbox_events_causation_id", "outbox_events", ["causation_id"])
    op.create_index("ix_outbox_events_status", "outbox_events", ["status"])
    op.create_index("ix_outbox_events_available_at", "outbox_events", ["available_at"])
    op.create_index(
        "ix_outbox_eligible",
        "outbox_events",
        ["status", "available_at", "occurred_at"],
    )
    op.create_index(
        "ix_outbox_owner_status", "outbox_events", ["owner_user_id", "status"]
    )

    op.create_table(
        "outbox_transitions",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column(
            "event_id", sa.String(64), sa.ForeignKey("outbox_events.id"), nullable=False
        ),
        sa.Column("sequence", sa.Integer(), nullable=False),
        sa.Column("cycle", sa.Integer(), nullable=False),
        sa.Column("attempt_number", sa.Integer(), nullable=False),
        sa.Column("transition", sa.String(32), nullable=False),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("worker_id", sa.String(64), nullable=True),
        sa.Column("lease_token", sa.String(64), nullable=True),
        sa.Column("actor_id", sa.String(64), nullable=True),
        sa.Column("failure_code", sa.String(64), nullable=True),
        sa.Column("policy_result", sa.String(160), nullable=True),
        sa.Column("reason", sa.String(240), nullable=True),
        sa.UniqueConstraint(
            "event_id", "sequence", name="uq_outbox_transition_sequence"
        ),
        sa.CheckConstraint("sequence >= 1", name="ck_outbox_transition_sequence"),
        sa.CheckConstraint("cycle >= 0", name="ck_outbox_transition_cycle"),
        sa.CheckConstraint("attempt_number >= 0", name="ck_outbox_transition_attempt"),
        sa.CheckConstraint(
            "transition IN ('claimed', 'reclaimed', 'retry_scheduled', "
            "'delivered', 'failed', 'recovered', 'duplicate_suppressed')",
            name="ck_outbox_transition_type",
        ),
    )
    op.create_index("ix_outbox_transitions_event_id", "outbox_transitions", ["event_id"])
    op.create_index(
        "ix_outbox_transition_event_time",
        "outbox_transitions",
        ["event_id", "occurred_at"],
    )

    op.create_table(
        "internal_effects",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("consumer_name", sa.String(120), nullable=False),
        sa.Column(
            "event_id", sa.String(64), sa.ForeignKey("outbox_events.id"), nullable=False
        ),
        sa.Column("owner_user_id", sa.String(64), nullable=False),
        sa.Column("effect_type", sa.String(120), nullable=False),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("payload_json", sa.Text(), nullable=False),
        sa.UniqueConstraint(
            "consumer_name", "event_id", name="uq_internal_effect_consumer_event"
        ),
    )
    op.create_index("ix_internal_effects_event_id", "internal_effects", ["event_id"])
    op.create_index(
        "ix_internal_effects_owner_user_id", "internal_effects", ["owner_user_id"]
    )

    op.create_table(
        "consumer_receipts",
        sa.Column("consumer_name", sa.String(120), primary_key=True),
        sa.Column(
            "event_id",
            sa.String(64),
            sa.ForeignKey("outbox_events.id"),
            primary_key=True,
        ),
        sa.Column(
            "effect_id", sa.String(64), sa.ForeignKey("internal_effects.id"), nullable=False
        ),
        sa.Column("processed_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint(
            "consumer_name", "event_id", name="uq_consumer_event_receipt"
        ),
    )

    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.execute(
            """
            CREATE FUNCTION personal_os_reject_outbox_transition_mutation()
            RETURNS trigger
            LANGUAGE plpgsql
            AS $$
            BEGIN
                RAISE EXCEPTION 'outbox_transitions are append-only'
                    USING ERRCODE = 'integrity_constraint_violation';
            END;
            $$
            """
        )
        op.execute(
            """
            CREATE TRIGGER trg_outbox_transitions_append_only
            BEFORE UPDATE OR DELETE ON outbox_transitions
            FOR EACH ROW EXECUTE FUNCTION personal_os_reject_outbox_transition_mutation()
            """
        )


def downgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.execute(
            "DROP TRIGGER IF EXISTS trg_outbox_transitions_append_only "
            "ON outbox_transitions"
        )
        op.execute("DROP FUNCTION IF EXISTS personal_os_reject_outbox_transition_mutation()")
    op.drop_table("consumer_receipts")
    op.drop_table("internal_effects")
    op.drop_table("outbox_transitions")
    op.drop_table("outbox_events")
