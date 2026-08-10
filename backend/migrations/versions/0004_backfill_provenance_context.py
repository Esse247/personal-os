"""Backfill required provenance context on pre-envelope synthetic rows.

Revision ID: 0004_backfill_provenance_context
Revises: 0003_integrity_envelopes
Create Date: 2026-08-10
"""

import json

import sqlalchemy as sa
from alembic import op

revision = "0004_backfill_provenance_context"
down_revision = "0003_integrity_envelopes"
branch_labels = None
depends_on = None

PROVENANCE_TABLES = (
    "world_facts",
    "financial_transactions",
    "transaction_classifications",
    "intents",
    "commitments",
    "schedule_proposals",
)


def upgrade() -> None:
    connection = op.get_bind()
    for table_name in PROVENANCE_TABLES:
        rows = connection.execute(
            sa.text(f"SELECT id, provenance_json FROM {table_name}")
        ).mappings()
        for row in rows:
            payload = json.loads(row["provenance_json"])
            if "actor_id" in payload:
                continue
            source_type = payload.get("source_type", "SYSTEM_INFERRED")
            payload.update(
                {
                    "actor_id": (
                        "legacy-synthetic-user"
                        if source_type == "USER_STATED"
                        else "migration-system"
                    ),
                    "data_subject_id": "legacy-synthetic-user",
                    "controller_id": "legacy-synthetic-user",
                    "correlation_id": "migration-0004",
                    "input_references": [],
                    "supersedes_reference": None,
                }
            )
            connection.execute(
                sa.text(
                    f"UPDATE {table_name} SET provenance_json = :payload WHERE id = :entity_id"
                ),
                {
                    "payload": json.dumps(payload, sort_keys=True),
                    "entity_id": row["id"],
                },
            )


def downgrade() -> None:
    # Context backfill is intentionally retained; removing attribution would lose evidence.
    pass
