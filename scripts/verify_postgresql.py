from __future__ import annotations

import json
import os
import subprocess
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import psycopg
from alembic.config import Config
from alembic.script import ScriptDirectory
from personal_os.adapters.persistence.database import (
    POSTGRESQL_SCHEMA_HEAD,
    assert_postgresql_schema_current,
    create_database_engine,
)
from psycopg import sql
from sqlalchemy.engine import URL, make_url

ALLOWED_HOSTS = {"127.0.0.1", "localhost", "postgres"}
EXPECTED_USER = "personal_os"
EXPECTED_PASSWORD = "personal_os_local_only"
EXPECTED_DATABASE = "personal_os_verify"
EXPECTED_UPGRADE_DATABASE = "personal_os_upgrade_verify"
FOUNDATION_V01_HEAD = "0005_calendar_snapshot_binding"
HISTORICAL_FIXTURE_COUNTS = {
    "world_facts_count": 1,
    "financial_transactions_count": 1,
    "audit_events_count": 1,
    "commitments_count": 1,
    "schedule_proposals_count": 1,
    "approvals_count": 1,
    "command_receipts_count": 1,
}


def validated_url(raw: str, *, expected_database: str) -> URL:
    try:
        url = make_url(raw)
    except Exception as exc:
        raise ValueError("PostgreSQL verification URL is invalid") from exc
    if url.get_backend_name() != "postgresql":
        raise ValueError("PostgreSQL verification requires a PostgreSQL URL")
    if url.host not in ALLOWED_HOSTS:
        raise ValueError(
            "PostgreSQL verification is restricted to the local CI/runtime service"
        )
    if url.username != EXPECTED_USER or url.password != EXPECTED_PASSWORD:
        raise ValueError(
            "PostgreSQL verification requires the documented synthetic account"
        )
    if url.database != expected_database:
        raise ValueError(
            f"PostgreSQL verification database must be {expected_database}"
        )
    return url


def psycopg_dsn(url: URL) -> str:
    return url.set(drivername="postgresql").render_as_string(hide_password=False)


def recreate_database(admin_url: URL, database_url: URL) -> None:
    database_name = str(database_url.database)
    with (
        psycopg.connect(psycopg_dsn(admin_url), autocommit=True) as connection,
        connection.cursor() as cursor,
    ):
        cursor.execute(
            "SELECT pg_terminate_backend(pid) FROM pg_stat_activity "
            "WHERE datname = %s AND pid <> pg_backend_pid()",
            (database_name,),
        )
        cursor.execute(
            sql.SQL("DROP DATABASE IF EXISTS {}").format(sql.Identifier(database_name))
        )
        cursor.execute(
            sql.SQL(
                "CREATE DATABASE {} OWNER {} TEMPLATE template0 ENCODING 'UTF8'"
            ).format(sql.Identifier(database_name), sql.Identifier(EXPECTED_USER))
        )


def environment_for(database_url: URL) -> dict[str, str]:
    environment = os.environ.copy()
    environment.update(
        {
            "PERSONAL_OS_ENV": "test",
            "PERSONAL_OS_PROVIDER_MODE": "mock",
            "PERSONAL_OS_DATABASE_URL": database_url.render_as_string(
                hide_password=False
            ),
            "PERSONAL_OS_AUTO_INITIALIZE": "false",
        }
    )
    return environment


def seed_foundation_v01_state(database_url: URL) -> None:
    """Seed only columns present at the immutable Foundation v0.1 revision.

    This verifier-owned fixture must not import current mapped models or invoke the
    application CLI: both intentionally reject a database that is not at head.
    """
    now = datetime(2026, 8, 10, 12, 0, tzinfo=UTC)
    provenance_payload = {
        "actor_id": "user-alex-synthetic",
        "confidence": 1.0,
        "confirmation_status": "confirmed",
        "controller_id": "user-alex-synthetic",
        "correlation_id": "postgresql-upgrade-v01",
        "data_subject_id": "user-alex-synthetic",
        "input_references": [],
        "observed_at": now.isoformat(),
        "recorded_at": now.isoformat(),
        "sensitivity": "personal",
        "source_identifier": "postgresql-upgrade:v01",
        "source_type": "USER_STATED",
        "supersedes_reference": None,
        "valid_from": None,
        "valid_until": None,
    }
    provenance = json.dumps(provenance_payload, sort_keys=True)
    transaction_provenance = json.dumps(
        {
            **provenance_payload,
            "confidence": 0.99,
            "source_identifier": "mock-bank:postgresql-upgrade-v01",
            "source_type": "TOOL_OBSERVED",
        },
        sort_keys=True,
    )
    with (
        psycopg.connect(psycopg_dsn(database_url)) as connection,
        connection.cursor() as cursor,
    ):
        cursor.execute(
            """
                INSERT INTO world_facts (
                    id, user_id, fact_type, label, occurs_at,
                    provenance_json, created_at
                ) VALUES (%s, %s, %s, %s, %s, %s, %s)
                """,
            (
                "postgresql-upgrade-world-fact-v01",
                "user-alex-synthetic",
                "milestone",
                "Synthetic Foundation v0.1 checkpoint",
                now + timedelta(days=30),
                provenance,
                now,
            ),
        )
        cursor.execute(
            """
                INSERT INTO financial_transactions (
                    id, user_id, household_id, project_id, merchant, memo,
                    amount_minor, currency, posted_at, provenance_json, created_at
                ) VALUES (%s, %s, %s, NULL, %s, %s, %s, %s, %s, %s, %s)
                """,
            (
                "postgresql-upgrade-transaction-v01",
                "user-alex-synthetic",
                "household-synthetic",
                "Synthetic hardware store",
                "Deterministic historical upgrade fixture",
                12500,
                "GBP",
                now - timedelta(days=1),
                transaction_provenance,
                now,
            ),
        )
        cursor.execute(
            """
                INSERT INTO commitments (
                    id, user_id, title, status, due_at, duration_minutes,
                    provenance_json, created_at, schedule_block_id, waiting_reason,
                    review_at, abandoned_reason, version
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, NULL, NULL, NULL, NULL, 1)
                """,
            (
                "postgresql-upgrade-commitment-v01",
                "user-alex-synthetic",
                "Preserved v0.1 commitment",
                "captured",
                now + timedelta(days=1),
                60,
                provenance,
                now,
            ),
        )
        cursor.execute(
            """
                INSERT INTO schedule_proposals (
                    id, user_id, commitment_id, starts_at, ends_at, status,
                    rationale, input_snapshot_hash, revision, created_at,
                    provenance_json, calendar_provider_id, calendar_snapshot_version,
                    supersedes_id, version
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, 1, %s, %s, %s, %s, NULL, 1)
                """,
            (
                "postgresql-upgrade-proposal-v01",
                "user-alex-synthetic",
                "postgresql-upgrade-commitment-v01",
                now + timedelta(hours=1),
                now + timedelta(hours=2),
                "proposed",
                "Representative accepted Foundation v0.1 proposal.",
                "a" * 64,
                now,
                provenance,
                "deterministic-calendar-v1",
                "snapshot-v01",
            ),
        )
        cursor.execute(
            """
                INSERT INTO audit_events (
                    id, user_id, action, entity_type, entity_id, correlation_id,
                    occurred_at, outcome, source_type, summary, details_json,
                    source_identifier, actor_id, on_behalf_of_id, entity_version,
                    causation_id, policy_result, capability_mode, approval_id,
                    tool_reference, agent_reference
                ) VALUES (
                    %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                    %s, %s, %s, 1, %s, %s, %s, %s, NULL, NULL
                )
                """,
            (
                "postgresql-upgrade-audit-v01",
                "user-alex-synthetic",
                "schedule.approval.recorded",
                "schedule_proposal",
                "postgresql-upgrade-proposal-v01",
                "postgresql-upgrade-v01",
                now,
                "success",
                "SYSTEM_INFERRED",
                "Representative accepted Foundation v0.1 audit record.",
                json.dumps({"synthetic_fixture": True}, sort_keys=True),
                "postgresql-verifier:foundation-v01",
                "user-alex-synthetic",
                "user-alex-synthetic",
                "postgresql-upgrade-v01",
                "allowed:synthetic-upgrade-fixture",
                "local-mock-synthetic",
                "postgresql-upgrade-approval-v01",
            ),
        )
        cursor.execute(
            """
                INSERT INTO approvals (
                    id, user_id, proposal_id, status, action_digest,
                    proposal_version, policy_version, expires_at, nonce,
                    idempotency_key, created_at, requester_id, approver_id,
                    permission, action_level, environment, target_type, target_id,
                    consumed_at, provider_id, on_behalf_of_id, disclosed_data,
                    audience, reversible, expected_consequence, commitment_version,
                    input_snapshot_hash, calendar_provider_id, calendar_snapshot_version
                ) VALUES (
                    %s, %s, %s, %s, %s, 1, %s, %s, %s, %s, %s, %s, %s,
                    %s, 3, %s, %s, %s, NULL, %s, %s, %s, %s, TRUE, %s, 1,
                    %s, %s, %s
                )
                """,
            (
                "postgresql-upgrade-approval-v01",
                "user-alex-synthetic",
                "postgresql-upgrade-proposal-v01",
                "approved",
                "b" * 64,
                "foundation-policy-v1",
                now + timedelta(hours=1),
                "postgresql-upgrade-nonce-v01",
                "postgresql-upgrade-approval-key-v01",
                now,
                "user-alex-synthetic",
                "user-alex-synthetic",
                "schedule.proposal.decide.own",
                "development-mock",
                "schedule_proposal",
                "postgresql-upgrade-proposal-v01",
                "internal:none",
                "user-alex-synthetic",
                "schedule proposal",
                "local user only",
                "schedule proposal may become a local confirmed block",
                "a" * 64,
                "deterministic-calendar-v1",
                "snapshot-v01",
            ),
        )
        cursor.execute(
            """
                INSERT INTO command_receipts (
                    idempotency_key, user_id, command_type, request_digest,
                    created_at, intent_id, commitment_id, proposal_id,
                    replacement_proposal_id
                ) VALUES (%s, %s, %s, %s, %s, NULL, %s, %s, NULL)
                """,
            (
                "postgresql-upgrade-receipt-v01",
                "user-alex-synthetic",
                "schedule_decision",
                "c" * 64,
                now,
                "postgresql-upgrade-commitment-v01",
                "postgresql-upgrade-proposal-v01",
            ),
        )


def historical_snapshot(database_url: URL) -> dict[str, Any]:
    tables = (
        "world_facts",
        "financial_transactions",
        "audit_events",
        "commitments",
        "schedule_proposals",
        "approvals",
        "command_receipts",
    )
    snapshot: dict[str, Any] = {}
    with (
        psycopg.connect(psycopg_dsn(database_url)) as connection,
        connection.cursor() as cursor,
    ):
        for table in tables:
            cursor.execute(
                sql.SQL("SELECT count(*) FROM {}").format(sql.Identifier(table))
            )
            row = cursor.fetchone()
            if row is None:
                raise RuntimeError(f"could not count historical table {table}")
            snapshot[f"{table}_count"] = row[0]
        cursor.execute(
            "SELECT provenance_json FROM commitments WHERE id = %s",
            ("postgresql-upgrade-commitment-v01",),
        )
        row = cursor.fetchone()
        if row is None:
            raise RuntimeError("historical commitment was not persisted")
        snapshot["commitment_provenance"] = row[0]
        cursor.execute(
            "SELECT action_digest FROM approvals WHERE id = %s",
            ("postgresql-upgrade-approval-v01",),
        )
        row = cursor.fetchone()
        if row is None:
            raise RuntimeError("historical approval was not persisted")
        snapshot["approval_digest"] = row[0]
        cursor.execute(
            "SELECT request_digest FROM command_receipts WHERE idempotency_key = %s",
            ("postgresql-upgrade-receipt-v01",),
        )
        row = cursor.fetchone()
        if row is None:
            raise RuntimeError("historical command receipt was not persisted")
        snapshot["receipt_digest"] = row[0]
        cursor.execute(
            """
                SELECT action, entity_id, correlation_id, policy_result,
                       capability_mode, approval_id
                FROM audit_events WHERE id = %s
                """,
            ("postgresql-upgrade-audit-v01",),
        )
        row = cursor.fetchone()
        if row is None:
            raise RuntimeError("historical audit event was not persisted")
        snapshot["audit_contract"] = {
            "action": row[0],
            "entity_id": row[1],
            "correlation_id": row[2],
            "policy_result": row[3],
            "capability_mode": row[4],
            "approval_id": row[5],
        }
    return snapshot


def assert_historical_fixture_snapshot(snapshot: dict[str, Any]) -> None:
    missing_or_unexpected = {
        key: snapshot.get(key)
        for key, expected in HISTORICAL_FIXTURE_COUNTS.items()
        if snapshot.get(key) != expected
    }
    if missing_or_unexpected:
        raise RuntimeError(
            f"historical Foundation v0.1 fixture is incomplete: {missing_or_unexpected}"
        )
    try:
        provenance = json.loads(snapshot["commitment_provenance"])
    except (KeyError, TypeError, json.JSONDecodeError) as exc:
        raise RuntimeError(
            "historical Foundation v0.1 provenance is missing or malformed"
        ) from exc
    if (
        provenance.get("source_type") != "USER_STATED"
        or provenance.get("correlation_id") != "postgresql-upgrade-v01"
    ):
        raise RuntimeError("historical Foundation v0.1 provenance changed")
    if snapshot.get("approval_digest") != "b" * 64:
        raise RuntimeError("historical Foundation v0.1 approval digest changed")
    if snapshot.get("receipt_digest") != "c" * 64:
        raise RuntimeError("historical Foundation v0.1 receipt digest changed")
    expected_audit = {
        "action": "schedule.approval.recorded",
        "entity_id": "postgresql-upgrade-proposal-v01",
        "correlation_id": "postgresql-upgrade-v01",
        "policy_result": "allowed:synthetic-upgrade-fixture",
        "capability_mode": "local-mock-synthetic",
        "approval_id": "postgresql-upgrade-approval-v01",
    }
    if snapshot.get("audit_contract") != expected_audit:
        raise RuntimeError("historical Foundation v0.1 audit contract changed")


def current_alembic_head(root: Path) -> str:
    configuration = Config(str(root / "backend/alembic.ini"))
    head = ScriptDirectory.from_config(configuration).get_current_head()
    if head is None:
        raise RuntimeError("Alembic migration history has no current head")
    return head


def verify_historical_upgrade(
    *, root: Path, database_url: URL, environment: dict[str, str]
) -> str:
    run_checked(
        [
            sys.executable,
            "-m",
            "alembic",
            "-c",
            "backend/alembic.ini",
            "upgrade",
            FOUNDATION_V01_HEAD,
        ],
        root=root,
        environment=environment,
    )
    stale_engine = create_database_engine(
        database_url.render_as_string(hide_password=False)
    )
    try:
        try:
            assert_postgresql_schema_current(stale_engine)
        except RuntimeError:
            pass
        else:
            raise RuntimeError("application accepted the stale Foundation v0.1 schema")
    finally:
        stale_engine.dispose()
    seed_foundation_v01_state(database_url)
    before = historical_snapshot(database_url)
    assert_historical_fixture_snapshot(before)
    run_checked(
        [
            sys.executable,
            "-m",
            "alembic",
            "-c",
            "backend/alembic.ini",
            "upgrade",
            "head",
        ],
        root=root,
        environment=environment,
    )
    after = historical_snapshot(database_url)
    if before != after:
        raise RuntimeError(
            "populated Foundation v0.1 state changed during PostgreSQL upgrade"
        )
    assert_historical_fixture_snapshot(after)
    expected_head = current_alembic_head(root)
    if expected_head != POSTGRESQL_SCHEMA_HEAD:
        raise RuntimeError(
            f"runtime schema head {POSTGRESQL_SCHEMA_HEAD} does not match Alembic {expected_head}"
        )
    current_engine = create_database_engine(
        database_url.render_as_string(hide_password=False)
    )
    try:
        assert_postgresql_schema_current(current_engine)
    finally:
        current_engine.dispose()
    with psycopg.connect(psycopg_dsn(database_url)) as connection:
        row = connection.execute("SELECT version_num FROM alembic_version").fetchone()
    if row is None:
        raise RuntimeError("historical upgrade did not create an Alembic version row")
    actual_head = row[0]
    if actual_head != expected_head:
        raise RuntimeError(
            f"historical upgrade ended at {actual_head}, expected {expected_head}"
        )
    return expected_head


def run_checked(command: list[str], *, root: Path, environment: dict[str, str]) -> None:
    completed = subprocess.run(command, cwd=root, env=environment, check=False)
    if completed.returncode != 0:
        raise RuntimeError(
            f"PostgreSQL verification command failed with exit {completed.returncode}: "
            f"{' '.join(command[:4])}"
        )


def main() -> None:
    test_raw = os.getenv("PERSONAL_OS_POSTGRES_TEST_URL")
    if not test_raw:
        raise RuntimeError("PERSONAL_OS_POSTGRES_TEST_URL is required")
    database_url = validated_url(test_raw, expected_database=EXPECTED_DATABASE)
    upgrade_raw = os.getenv("PERSONAL_OS_POSTGRES_UPGRADE_URL")
    if not upgrade_raw:
        raise RuntimeError("PERSONAL_OS_POSTGRES_UPGRADE_URL is required")
    upgrade_url = validated_url(
        upgrade_raw, expected_database=EXPECTED_UPGRADE_DATABASE
    )
    admin_raw = os.getenv("PERSONAL_OS_POSTGRES_ADMIN_URL")
    admin_url = validated_url(
        admin_raw
        or database_url.set(database="postgres").render_as_string(hide_password=False),
        expected_database="postgres",
    )
    recreate_database(admin_url, database_url)
    recreate_database(admin_url, upgrade_url)

    root = Path(__file__).resolve().parents[1]
    historical_head = verify_historical_upgrade(
        root=root,
        database_url=upgrade_url,
        environment=environment_for(upgrade_url),
    )
    environment = environment_for(database_url)
    commands = [
        [
            sys.executable,
            "-m",
            "alembic",
            "-c",
            "backend/alembic.ini",
            "upgrade",
            "head",
        ],
        [
            sys.executable,
            "-m",
            "alembic",
            "-c",
            "backend/alembic.ini",
            "upgrade",
            "head",
        ],
        [sys.executable, "-m", "personal_os.cli", "fixtures-load"],
        [sys.executable, "-m", "personal_os.cli", "fixtures-load"],
        [sys.executable, "-m", "pytest", "backend/tests/postgresql", "-q"],
    ]
    for command in commands:
        run_checked(command, root=root, environment=environment)
    print(
        json.dumps(
            {
                "database": EXPECTED_DATABASE,
                "dialect": "postgresql",
                "fixtures_loads": 2,
                "historical_from": FOUNDATION_V01_HEAD,
                "historical_to": historical_head,
                "historical_upgrade": "passed",
                "migration_passes": 2,
                "result": "passed",
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
