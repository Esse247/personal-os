"""Create the immutable Foundation v0.1 baseline schema.

Revision ID: 0001_foundation_schema
Revises: None
Create Date: 2026-08-10
"""

import sqlalchemy as sa
from alembic import op

revision = "0001_foundation_schema"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "commitments",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("user_id", sa.String(64), nullable=False),
        sa.Column("title", sa.String(240), nullable=False),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("due_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("duration_minutes", sa.Integer(), nullable=False),
        sa.Column("provenance_json", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("schedule_block_id", sa.String(64), nullable=True),
        sa.Column("waiting_reason", sa.Text(), nullable=True),
        sa.Column("review_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("abandoned_reason", sa.Text(), nullable=True),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
    )
    op.create_index("ix_commitments_user_id", "commitments", ["user_id"])
    op.create_index("ix_commitments_status", "commitments", ["status"])

    op.create_table(
        "intents",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("user_id", sa.String(64), nullable=False),
        sa.Column("raw_text", sa.Text(), nullable=False),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("provenance_json", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("title", sa.String(240), nullable=True),
        sa.Column("due_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("duration_minutes", sa.Integer(), nullable=True),
        sa.Column("clarification_question", sa.Text(), nullable=True),
        sa.Column("commitment_id", sa.String(64), nullable=True),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
    )
    op.create_index("ix_intents_user_id", "intents", ["user_id"])
    op.create_index("ix_intents_status", "intents", ["status"])

    op.create_table(
        "schedule_proposals",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("user_id", sa.String(64), nullable=False),
        sa.Column("commitment_id", sa.String(64), sa.ForeignKey("commitments.id")),
        sa.Column("starts_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ends_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("rationale", sa.Text(), nullable=False),
        sa.Column("input_snapshot_hash", sa.String(64), nullable=False),
        sa.Column("revision", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("supersedes_id", sa.String(64), nullable=True),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
    )
    op.create_index("ix_schedule_proposals_user_id", "schedule_proposals", ["user_id"])
    op.create_index(
        "ix_schedule_proposals_commitment_id", "schedule_proposals", ["commitment_id"]
    )
    op.create_index("ix_schedule_proposals_starts_at", "schedule_proposals", ["starts_at"])
    op.create_index("ix_schedule_proposals_status", "schedule_proposals", ["status"])

    op.create_table(
        "schedule_blocks",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("user_id", sa.String(64), nullable=False),
        sa.Column("commitment_id", sa.String(64), sa.ForeignKey("commitments.id")),
        sa.Column("starts_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ends_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_schedule_blocks_user_id", "schedule_blocks", ["user_id"])
    op.create_index("ix_schedule_blocks_commitment_id", "schedule_blocks", ["commitment_id"])
    op.create_index("ix_schedule_blocks_starts_at", "schedule_blocks", ["starts_at"])
    op.create_index("ix_schedule_blocks_status", "schedule_blocks", ["status"])

    op.create_table(
        "approvals",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("user_id", sa.String(64), nullable=False),
        sa.Column("proposal_id", sa.String(64), sa.ForeignKey("schedule_proposals.id")),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("action_digest", sa.String(64), nullable=False),
        sa.Column("proposal_version", sa.Integer(), nullable=False),
        sa.Column("policy_version", sa.String(64), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("nonce", sa.String(64), nullable=False, unique=True),
        sa.Column("idempotency_key", sa.String(128), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("idempotency_key", name="uq_approval_idempotency"),
    )
    op.create_index("ix_approvals_user_id", "approvals", ["user_id"])
    op.create_index("ix_approvals_proposal_id", "approvals", ["proposal_id"])
    op.create_index("ix_approvals_status", "approvals", ["status"])

    op.create_table(
        "world_facts",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("user_id", sa.String(64), nullable=False),
        sa.Column("fact_type", sa.String(64), nullable=False),
        sa.Column("label", sa.String(160), nullable=False),
        sa.Column("occurs_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("provenance_json", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_world_fact_user_label", "world_facts", ["user_id", "label"])

    op.create_table(
        "projects",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("user_id", sa.String(64), nullable=False),
        sa.Column("name", sa.String(240), nullable=False),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("is_primary", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_projects_user_id", "projects", ["user_id"])

    op.create_table(
        "financial_transactions",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("user_id", sa.String(64), nullable=False),
        sa.Column("household_id", sa.String(64), nullable=False),
        sa.Column("project_id", sa.String(64), nullable=True),
        sa.Column("merchant", sa.String(240), nullable=False),
        sa.Column("memo", sa.Text(), nullable=False),
        sa.Column("amount_minor", sa.Integer(), nullable=False),
        sa.Column("currency", sa.String(3), nullable=False),
        sa.Column("posted_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("provenance_json", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    for column in ("user_id", "household_id", "project_id", "posted_at"):
        op.create_index(
            f"ix_financial_transactions_{column}", "financial_transactions", [column]
        )

    op.create_table(
        "transaction_classifications",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column(
            "transaction_id", sa.String(64), sa.ForeignKey("financial_transactions.id")
        ),
        sa.Column("category", sa.String(160), nullable=False),
        sa.Column("rule_id", sa.String(120), nullable=False),
        sa.Column("confidence", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("provenance_json", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index(
        "ix_transaction_classifications_transaction_id",
        "transaction_classifications",
        ["transaction_id"],
    )

    op.create_table(
        "audit_events",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("user_id", sa.String(64), nullable=False),
        sa.Column("action", sa.String(120), nullable=False),
        sa.Column("entity_type", sa.String(80), nullable=False),
        sa.Column("entity_id", sa.String(64), nullable=False),
        sa.Column("correlation_id", sa.String(64), nullable=False),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("outcome", sa.String(32), nullable=False),
        sa.Column("source_type", sa.String(32), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("details_json", sa.Text(), nullable=False, server_default="{}"),
    )
    op.create_index("ix_audit_events_action", "audit_events", ["action"])
    op.create_index("ix_audit_events_entity_id", "audit_events", ["entity_id"])
    op.create_index("ix_audit_events_correlation_id", "audit_events", ["correlation_id"])
    op.create_index("ix_audit_user_time", "audit_events", ["user_id", "occurred_at"])


def downgrade() -> None:
    for table in (
        "audit_events",
        "transaction_classifications",
        "financial_transactions",
        "projects",
        "world_facts",
        "approvals",
        "schedule_blocks",
        "schedule_proposals",
        "intents",
        "commitments",
    ):
        op.drop_table(table)
