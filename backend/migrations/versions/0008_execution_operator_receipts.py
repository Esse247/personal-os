"""Bind recover commands to durable exact-replay results.

Revision ID: 0008_operator_receipts
Revises: 0007_outbox_execution
Create Date: 2026-08-10
"""

import sqlalchemy as sa
from alembic import op

revision = "0008_operator_receipts"
down_revision = "0007_outbox_execution"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("command_receipts") as batch:
        batch.add_column(sa.Column("outbox_event_id", sa.String(64), nullable=True))
        batch.add_column(sa.Column("result_json", sa.Text(), nullable=True))
        batch.create_foreign_key(
            "fk_command_receipt_outbox_event",
            "outbox_events",
            ["outbox_event_id"],
            ["id"],
        )
        batch.create_check_constraint(
            "ck_command_receipt_outbox_result_pair",
            "(outbox_event_id IS NULL AND result_json IS NULL) OR "
            "(outbox_event_id IS NOT NULL AND result_json IS NOT NULL)",
        )
        batch.create_check_constraint(
            "ck_command_receipt_result_size",
            "result_json IS NULL OR length(result_json) <= 2048",
        )
        batch.create_index("ix_command_receipts_outbox_event_id", ["outbox_event_id"], unique=False)


def downgrade() -> None:
    with op.batch_alter_table("command_receipts") as batch:
        batch.drop_index("ix_command_receipts_outbox_event_id")
        batch.drop_constraint("ck_command_receipt_result_size", type_="check")
        batch.drop_constraint("ck_command_receipt_outbox_result_pair", type_="check")
        batch.drop_constraint("fk_command_receipt_outbox_event", type_="foreignkey")
        batch.drop_column("result_json")
        batch.drop_column("outbox_event_id")
