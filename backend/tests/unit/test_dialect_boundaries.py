from __future__ import annotations

from pathlib import Path
from typing import cast

import pytest
from alembic.config import Config
from alembic.script import ScriptDirectory
from scripts.validate_postgresql_ci import validate
from scripts.verify_postgresql import (
    HISTORICAL_FIXTURE_COUNTS,
    assert_historical_fixture_snapshot,
    validated_url,
)
from sqlalchemy import Engine, create_mock_engine
from sqlalchemy.dialects import postgresql
from sqlalchemy.schema import CreateTable

from personal_os.adapters.persistence.database import (
    POSTGRESQL_SCHEMA_HEAD,
    assert_postgresql_schema_current,
    initialize_schema,
)
from personal_os.adapters.persistence.models import Base

ROOT = Path(__file__).resolve().parents[3]


def test_all_mapped_tables_compile_for_postgresql() -> None:
    for table in Base.metadata.sorted_tables:
        compiled = str(CreateTable(table).compile(dialect=postgresql.dialect()))
        assert f"CREATE TABLE {table.name}" in compiled


def test_postgresql_cannot_use_sqlite_create_all_bootstrap() -> None:
    engine = cast(
        Engine,
        create_mock_engine(
            "postgresql+psycopg://personal_os@localhost/personal_os",
            lambda *_: None,
        ),
    )
    with pytest.raises(RuntimeError, match="Alembic migrations"):
        initialize_schema(engine)


def test_runtime_postgresql_schema_head_matches_alembic_and_sqlite_is_exempt() -> None:
    configuration = Config(str(ROOT / "backend/alembic.ini"))
    script = ScriptDirectory.from_config(configuration)
    assert script.get_current_head() == POSTGRESQL_SCHEMA_HEAD
    assert all(len(revision.revision) <= 32 for revision in script.walk_revisions())
    from sqlalchemy import create_engine

    sqlite_engine = create_engine("sqlite+pysqlite:///:memory:")
    assert_postgresql_schema_current(sqlite_engine)


def test_persistence_source_has_no_unscoped_sqlite_production_idiom() -> None:
    source = (ROOT / "backend/src/personal_os/adapters/persistence/repositories.py").read_text(
        encoding="utf-8"
    )
    for forbidden in ("INSERT OR ", "last_insert_rowid", "PRAGMA ", "datetime('now')"):
        assert forbidden.casefold() not in source.casefold()
    assert "pg_advisory_xact_lock" in source
    assert "hashtextextended" in source
    assert "func.clock_timestamp() if is_postgresql" in source
    assert source.count("OutboxEventRow.lease_expires_at > database_time") == 2


def test_postgresql_verifier_rejects_remote_or_credential_shaped_targets() -> None:
    valid = (
        "postgresql+psycopg://personal_os:personal_os_local_only@localhost:5432/personal_os_verify"
    )
    assert validated_url(valid, expected_database="personal_os_verify").database == (
        "personal_os_verify"
    )
    with pytest.raises(ValueError, match="local CI/runtime"):
        validated_url(
            valid.replace("localhost", "database.example"),
            expected_database="personal_os_verify",
        )
    with pytest.raises(ValueError, match="synthetic account"):
        validated_url(
            valid.replace("personal_os_local_only", "real-secret"),
            expected_database="personal_os_verify",
        )
    with pytest.raises(ValueError, match="must be personal_os_verify"):
        validated_url(
            valid.replace("personal_os_verify", "personal_os"),
            expected_database="personal_os_verify",
        )


def test_postgresql_ci_contract_is_reproducible_and_mock_only() -> None:
    assert validate(ROOT) == []


def test_historical_upgrade_verifier_uses_revision_pinned_fixture_seed() -> None:
    source = (ROOT / "scripts/verify_postgresql.py").read_text(encoding="utf-8")
    historical_path = source.split("def verify_historical_upgrade", maxsplit=1)[1].split(
        "def run_checked", maxsplit=1
    )[0]
    assert "personal_os.cli" not in historical_path
    assert "seed_foundation_v01_state(database_url)" in historical_path
    assert historical_path.count("assert_historical_fixture_snapshot(") == 2


def test_historical_upgrade_fixture_requires_representative_v01_evidence() -> None:
    valid = {
        **HISTORICAL_FIXTURE_COUNTS,
        "commitment_provenance": (
            '{"source_type":"USER_STATED","correlation_id":"postgresql-upgrade-v01"}'
        ),
        "approval_digest": "b" * 64,
        "receipt_digest": "c" * 64,
        "audit_contract": {
            "action": "schedule.approval.recorded",
            "entity_id": "postgresql-upgrade-proposal-v01",
            "correlation_id": "postgresql-upgrade-v01",
            "policy_result": "allowed:synthetic-upgrade-fixture",
            "capability_mode": "local-mock-synthetic",
            "approval_id": "postgresql-upgrade-approval-v01",
        },
    }
    assert_historical_fixture_snapshot(valid)

    incomplete = {**valid, "audit_events_count": 0}
    with pytest.raises(RuntimeError, match="fixture is incomplete"):
        assert_historical_fixture_snapshot(incomplete)

    mutated = {**valid, "receipt_digest": "d" * 64}
    with pytest.raises(RuntimeError, match="receipt digest changed"):
        assert_historical_fixture_snapshot(mutated)
