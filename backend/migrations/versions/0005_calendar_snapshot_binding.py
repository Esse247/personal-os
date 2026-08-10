"""Bind proposals and approvals to calendar snapshot identity.

Revision ID: 0005_calendar_snapshot_binding
Revises: 0004_backfill_provenance_context
Create Date: 2026-08-10
"""

import sqlalchemy as sa
from alembic import op

revision = "0005_calendar_snapshot_binding"
down_revision = "0004_backfill_provenance_context"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "schedule_proposals",
        sa.Column(
            "calendar_provider_id",
            sa.String(120),
            nullable=False,
            server_default="legacy-calendar-mock",
        ),
    )
    op.add_column(
        "schedule_proposals",
        sa.Column(
            "calendar_snapshot_version",
            sa.String(120),
            nullable=False,
            server_default="legacy-snapshot",
        ),
    )
    op.add_column(
        "approvals",
        sa.Column(
            "input_snapshot_hash",
            sa.String(64),
            nullable=False,
            server_default="0" * 64,
        ),
    )
    op.add_column(
        "approvals",
        sa.Column(
            "calendar_provider_id",
            sa.String(120),
            nullable=False,
            server_default="legacy-calendar-mock",
        ),
    )
    op.add_column(
        "approvals",
        sa.Column(
            "calendar_snapshot_version",
            sa.String(120),
            nullable=False,
            server_default="legacy-snapshot",
        ),
    )


def downgrade() -> None:
    for name in (
        "calendar_snapshot_version",
        "calendar_provider_id",
        "input_snapshot_hash",
    ):
        op.drop_column("approvals", name)
    op.drop_column("schedule_proposals", "calendar_snapshot_version")
    op.drop_column("schedule_proposals", "calendar_provider_id")
