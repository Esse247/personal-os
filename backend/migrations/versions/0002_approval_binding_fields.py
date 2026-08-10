"""Add explicit approval authority and target binding fields.

Revision ID: 0002_approval_binding_fields
Revises: 0001_foundation_schema
Create Date: 2026-08-10
"""

import sqlalchemy as sa
from alembic import op

revision = "0002_approval_binding_fields"
down_revision = "0001_foundation_schema"
branch_labels = None
depends_on = None


def upgrade() -> None:
    existing = {column["name"] for column in sa.inspect(op.get_bind()).get_columns("approvals")}
    columns = (
        sa.Column(
            "requester_id", sa.String(length=64), nullable=False, server_default="system"
        ),
        sa.Column("approver_id", sa.String(length=64), nullable=False, server_default="user"),
        sa.Column(
            "permission",
            sa.String(length=120),
            nullable=False,
            server_default="schedule.proposal.decide.own",
        ),
        sa.Column("action_level", sa.Integer(), nullable=False, server_default="3"),
        sa.Column(
            "environment",
            sa.String(length=64),
            nullable=False,
            server_default="development-mock",
        ),
        sa.Column(
            "target_type",
            sa.String(length=80),
            nullable=False,
            server_default="schedule_proposal",
        ),
        sa.Column("target_id", sa.String(length=64), nullable=False, server_default="legacy"),
        sa.Column("consumed_at", sa.DateTime(timezone=True), nullable=True),
    )
    for column in columns:
        if column.name not in existing:
            op.add_column("approvals", column)


def downgrade() -> None:
    for name in (
        "consumed_at",
        "target_id",
        "target_type",
        "environment",
        "action_level",
        "permission",
        "approver_id",
        "requester_id",
    ):
        op.drop_column("approvals", name)
