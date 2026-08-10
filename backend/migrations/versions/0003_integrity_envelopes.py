"""Add command receipts, provenance, audit, approval, and schedule guards.

Revision ID: 0003_integrity_envelopes
Revises: 0002_approval_binding_fields
Create Date: 2026-08-10
"""

import json

import sqlalchemy as sa
from alembic import op

revision = "0003_integrity_envelopes"
down_revision = "0002_approval_binding_fields"
branch_labels = None
depends_on = None

LEGACY_PROVENANCE_JSON = json.dumps(
    {
        "source_type": "SYSTEM_INFERRED",
        "source_identifier": "migration:legacy-schedule-proposal",
        "observed_at": "2026-08-10T00:00:00+00:00",
        "recorded_at": "2026-08-10T00:00:00+00:00",
        "confidence": 0.0,
        "confirmation_status": "unconfirmed",
        "sensitivity": "personal",
        "actor_id": "migration-system",
        "data_subject_id": "legacy-synthetic-user",
        "controller_id": "legacy-synthetic-user",
        "correlation_id": "migration-0003",
        "valid_from": None,
        "valid_until": None,
        "input_references": [],
        "supersedes_reference": None,
    },
    sort_keys=True,
)


def upgrade() -> None:
    op.add_column(
        "schedule_proposals",
        sa.Column(
            "provenance_json",
            sa.Text(),
            nullable=False,
            server_default=LEGACY_PROVENANCE_JSON,
        ),
    )
    with op.batch_alter_table("schedule_blocks") as batch:
        batch.create_unique_constraint("uq_schedule_block_commitment", ["commitment_id"])
        batch.create_unique_constraint(
            "uq_schedule_block_exact_interval", ["user_id", "starts_at", "ends_at"]
        )
    op.create_index(
        "ix_schedule_block_user_interval",
        "schedule_blocks",
        ["user_id", "starts_at", "ends_at"],
    )

    approval_columns = (
        sa.Column("provider_id", sa.String(120), nullable=False, server_default="internal:none"),
        sa.Column(
            "on_behalf_of_id", sa.String(64), nullable=False, server_default="synthetic-user"
        ),
        sa.Column("disclosed_data", sa.Text(), nullable=False, server_default="none"),
        sa.Column("audience", sa.String(160), nullable=False, server_default="local user only"),
        sa.Column("reversible", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column(
            "expected_consequence",
            sa.Text(),
            nullable=False,
            server_default="legacy internal decision",
        ),
        sa.Column("commitment_version", sa.Integer(), nullable=False, server_default="1"),
    )
    for column in approval_columns:
        op.add_column("approvals", column)

    audit_columns = (
        sa.Column(
            "source_identifier", sa.String(240), nullable=False, server_default="legacy:unknown"
        ),
        sa.Column("actor_id", sa.String(64), nullable=False, server_default="legacy-system"),
        sa.Column("on_behalf_of_id", sa.String(64), nullable=True),
        sa.Column("entity_version", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("causation_id", sa.String(128), nullable=False, server_default="legacy"),
        sa.Column(
            "policy_result", sa.String(160), nullable=False, server_default="legacy:unknown"
        ),
        sa.Column(
            "capability_mode", sa.String(64), nullable=False, server_default="local-mock-synthetic"
        ),
        sa.Column("approval_id", sa.String(64), nullable=True),
        sa.Column("tool_reference", sa.String(240), nullable=True),
        sa.Column("agent_reference", sa.String(240), nullable=True),
    )
    for column in audit_columns:
        op.add_column("audit_events", column)
    op.create_index("ix_audit_events_actor_id", "audit_events", ["actor_id"])
    op.create_index("ix_audit_events_causation_id", "audit_events", ["causation_id"])

    op.create_table(
        "command_receipts",
        sa.Column("idempotency_key", sa.String(128), primary_key=True),
        sa.Column("user_id", sa.String(64), nullable=False),
        sa.Column("command_type", sa.String(80), nullable=False),
        sa.Column("request_digest", sa.String(64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("intent_id", sa.String(64), nullable=True),
        sa.Column("commitment_id", sa.String(64), nullable=True),
        sa.Column("proposal_id", sa.String(64), nullable=True),
        sa.Column("replacement_proposal_id", sa.String(64), nullable=True),
    )
    op.create_index("ix_command_receipts_user_id", "command_receipts", ["user_id"])


def downgrade() -> None:
    op.drop_table("command_receipts")
    op.drop_index("ix_audit_events_causation_id", table_name="audit_events")
    op.drop_index("ix_audit_events_actor_id", table_name="audit_events")
    for name in (
        "agent_reference",
        "tool_reference",
        "approval_id",
        "capability_mode",
        "policy_result",
        "causation_id",
        "entity_version",
        "on_behalf_of_id",
        "actor_id",
        "source_identifier",
    ):
        op.drop_column("audit_events", name)
    for name in (
        "commitment_version",
        "expected_consequence",
        "reversible",
        "audience",
        "disclosed_data",
        "on_behalf_of_id",
        "provider_id",
    ):
        op.drop_column("approvals", name)
    op.drop_index("ix_schedule_block_user_interval", table_name="schedule_blocks")
    with op.batch_alter_table("schedule_blocks") as batch:
        batch.drop_constraint("uq_schedule_block_exact_interval", type_="unique")
        batch.drop_constraint("uq_schedule_block_commitment", type_="unique")
    op.drop_column("schedule_proposals", "provenance_json")
