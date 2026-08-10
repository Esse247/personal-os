"""Enforce append-only audit rows under PostgreSQL production semantics.

Revision ID: 0006_pg_audit_immutable
Revises: 0005_calendar_snapshot_binding
Create Date: 2026-08-10
"""

from alembic import op

revision = "0006_pg_audit_immutable"
down_revision = "0005_calendar_snapshot_binding"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        return
    op.execute(
        """
        CREATE FUNCTION personal_os_reject_audit_mutation()
        RETURNS trigger
        LANGUAGE plpgsql
        AS $$
        BEGIN
            RAISE EXCEPTION 'audit_events are append-only'
                USING ERRCODE = 'integrity_constraint_violation';
        END;
        $$
        """
    )
    op.execute(
        """
        CREATE TRIGGER trg_audit_events_append_only
        BEFORE UPDATE OR DELETE ON audit_events
        FOR EACH ROW EXECUTE FUNCTION personal_os_reject_audit_mutation()
        """
    )


def downgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        return
    op.execute("DROP TRIGGER IF EXISTS trg_audit_events_append_only ON audit_events")
    op.execute("DROP FUNCTION IF EXISTS personal_os_reject_audit_mutation()")
