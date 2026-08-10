from __future__ import annotations

import json
from dataclasses import replace
from datetime import UTC, datetime
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import Engine, inspect, select, text
from sqlalchemy.orm import sessionmaker

from personal_os.adapters.persistence.models import (
    AuditEventRow,
    FinancialTransactionRow,
    ScheduleBlockRow,
)
from personal_os.adapters.persistence.repositories import SqlUnitOfWork, create_uow_factory
from personal_os.adapters.providers.mock import (
    DeterministicMockCalendarProvider,
    DeterministicMockModelProvider,
    SyntheticBankingProvider,
)
from personal_os.application.commands import (
    CaptureIntentCommand,
    DecideProposalCommand,
    ProposalDecision,
)
from personal_os.application.services import PersonalOSService
from personal_os.config import DEMO_USER_ID
from personal_os.domain.errors import ConflictError
from personal_os.domain.scheduling import CalendarSnapshot
from personal_os.fixtures import load_synthetic_fixtures
from personal_os.ports.providers import ProviderRequestContext, ProviderResult


class SpySyntheticBankingProvider(SyntheticBankingProvider):
    def __init__(self) -> None:
        self.calls = 0

    def read_synthetic_transactions(
        self, *, user_id: str, context: ProviderRequestContext
    ) -> ProviderResult[tuple[dict[str, object], ...]]:
        self.calls += 1
        return super().read_synthetic_transactions(user_id=user_id, context=context)


class ChangingCalendarProvider(DeterministicMockCalendarProvider):
    def __init__(self) -> None:
        self.calls = 0

    def availability(
        self, *, user_id: str, before_iso: str, context: ProviderRequestContext
    ) -> CalendarSnapshot:
        self.calls += 1
        snapshot = super().availability(
            user_id=user_id,
            before_iso=before_iso,
            context=context,
        )
        if self.calls > 1:
            return replace(snapshot, version="availability-snapshot-v2")
        return snapshot


def test_synthetic_fixtures_are_idempotent(engine: Engine) -> None:
    factory = create_uow_factory(engine)
    # The client lifespan is not required: initialize the schema through fixture helper's caller.
    from personal_os.adapters.persistence.database import initialize_schema

    initialize_schema(engine)
    banking = SpySyntheticBankingProvider()
    load_synthetic_fixtures(factory, banking)
    load_synthetic_fixtures(factory, banking)
    with engine.connect() as connection:
        transaction_count = len(connection.execute(select(FinancialTransactionRow.id)).all())
        audit_count = len(connection.execute(select(AuditEventRow.id)).all())
    assert transaction_count == 2
    assert audit_count == 2
    assert banking.calls == 1


def test_migration_applies_from_zero_and_reruns_safely(tmp_path: Path) -> None:
    database_path = tmp_path / "migration-test.db"
    root = Path(__file__).resolve().parents[3]
    config = Config(str(root / "backend" / "alembic.ini"))
    config.set_main_option("script_location", str(root / "backend" / "migrations"))
    config.set_main_option("sqlalchemy.url", f"sqlite:///{database_path.as_posix()}")
    command.upgrade(config, "head")
    command.upgrade(config, "head")

    from sqlalchemy import create_engine

    migrated_engine = create_engine(f"sqlite:///{database_path.as_posix()}")
    tables = set(inspect(migrated_engine).get_table_names())
    assert {
        "intents",
        "commitments",
        "schedule_proposals",
        "schedule_blocks",
        "approvals",
        "financial_transactions",
        "transaction_classifications",
        "audit_events",
        "command_receipts",
        "alembic_version",
    } <= tables


def test_migration_revisions_are_pinned_and_upgrade_historical_schema(tmp_path: Path) -> None:
    database_path = tmp_path / "historical-upgrade.db"
    root = Path(__file__).resolve().parents[3]
    config = Config(str(root / "backend" / "alembic.ini"))
    config.set_main_option("script_location", str(root / "backend" / "migrations"))
    config.set_main_option("sqlalchemy.url", f"sqlite:///{database_path.as_posix()}")
    command.upgrade(config, "0001_foundation_schema")

    from sqlalchemy import create_engine

    historical_engine = create_engine(f"sqlite:///{database_path.as_posix()}")
    historical_columns = {
        item["name"] for item in inspect(historical_engine).get_columns("approvals")
    }
    assert "requester_id" not in historical_columns
    assert "provider_id" not in historical_columns
    legacy_provenance = json.dumps(
        {
            "source_type": "USER_STATED",
            "source_identifier": "legacy:test",
            "observed_at": "2026-08-10T08:00:00+00:00",
            "recorded_at": "2026-08-10T08:00:00+00:00",
            "confidence": 1.0,
            "confirmation_status": "confirmed",
            "sensitivity": "personal",
            "valid_from": None,
            "valid_until": None,
        }
    )
    with historical_engine.begin() as connection:
        connection.execute(
            text(
                "INSERT INTO world_facts "
                "(id, user_id, fact_type, label, occurs_at, provenance_json, created_at) "
                "VALUES (:id, :user_id, :fact_type, :label, :occurs_at, :provenance, :created_at)"
            ),
            {
                "id": "legacy-world-fact",
                "user_id": "legacy-synthetic-user",
                "fact_type": "test",
                "label": "Legacy",
                "occurs_at": datetime(2026, 9, 1, tzinfo=UTC),
                "provenance": legacy_provenance,
                "created_at": datetime(2026, 8, 10, tzinfo=UTC),
            },
        )

    command.upgrade(config, "head")
    head_columns = {item["name"] for item in inspect(historical_engine).get_columns("approvals")}
    assert {
        "requester_id",
        "provider_id",
        "commitment_version",
        "input_snapshot_hash",
        "calendar_provider_id",
        "calendar_snapshot_version",
    } <= head_columns
    assert "command_receipts" in inspect(historical_engine).get_table_names()
    with historical_engine.connect() as connection:
        migrated_provenance = json.loads(
            connection.execute(
                text("SELECT provenance_json FROM world_facts WHERE id = 'legacy-world-fact'")
            ).scalar_one()
        )
    assert migrated_provenance["actor_id"] == "legacy-synthetic-user"
    assert migrated_provenance["correlation_id"] == "migration-0004"


def test_proposal_repository_uses_compare_and_swap(engine: Engine) -> None:
    from personal_os.adapters.persistence.database import initialize_schema

    initialize_schema(engine)
    factory = create_uow_factory(engine)
    load_synthetic_fixtures(factory)
    result = PersonalOSService(
        uow_factory=factory,
        model_provider=DeterministicMockModelProvider(),
        calendar_provider=DeterministicMockCalendarProvider(),
    ).capture_intent(
        CaptureIntentCommand(
            user_id=DEMO_USER_ID,
            raw_text="I need a haircut before the wedding next month.",
            correlation_id="cas-test-correlation",
            idempotency_key="cas-test-capture-0001",
        )
    )
    assert result.proposal is not None

    with factory() as first, factory() as second:
        first_copy = first.proposals.get(result.proposal.id)
        stale_copy = second.proposals.get(result.proposal.id)
        assert first_copy is not None and stale_copy is not None
        first_copy.approve(1)
        first.proposals.add(first_copy)
        first.commit()

        stale_copy.approve(1)
        with pytest.raises(ConflictError, match=r"stale|concurrently"):
            second.proposals.add(stale_copy)


def test_approval_revalidates_calendar_snapshot_binding(engine: Engine) -> None:
    from personal_os.adapters.persistence.database import initialize_schema

    initialize_schema(engine)
    factory = create_uow_factory(engine)
    load_synthetic_fixtures(factory)
    calendar = ChangingCalendarProvider()
    service = PersonalOSService(
        uow_factory=factory,
        model_provider=DeterministicMockModelProvider(),
        calendar_provider=calendar,
    )
    captured = service.capture_intent(
        CaptureIntentCommand(
            user_id=DEMO_USER_ID,
            raw_text="I need a haircut before the wedding next month.",
            correlation_id="snapshot-test-correlation",
            idempotency_key="snapshot-test-capture-0001",
        )
    )
    assert captured.proposal is not None
    with pytest.raises(ConflictError, match="availability changed"):
        service.decide_proposal(
            DecideProposalCommand(
                user_id=DEMO_USER_ID,
                proposal_id=captured.proposal.id,
                decision=ProposalDecision.APPROVE,
                expected_version=captured.proposal.version,
                correlation_id="snapshot-test-approval-correlation",
                idempotency_key="snapshot-test-approval-0001",
            )
        )
    with factory() as uow:
        assert uow.blocks.list_for_user(DEMO_USER_ID) == []
        denied = [
            event
            for event in uow.audit.list_for_user(DEMO_USER_ID)
            if event.action == "schedule.decision_denied"
        ]
        assert denied[-1].policy_result == "denied:stale-calendar-snapshot"


def test_losing_persistent_approval_race_records_denial_after_rollback(
    engine: Engine,
) -> None:
    """A database race loser must retain a denial after its whole UoW rolls back."""
    from personal_os.adapters.persistence.database import initialize_schema

    initialize_schema(engine)
    session_factory = sessionmaker(bind=engine, expire_on_commit=False)
    injected = False

    class RaceLosingUnitOfWork(SqlUnitOfWork):
        def commit(self) -> None:
            nonlocal injected
            session = self.session
            if (
                not injected
                and session is not None
                and any(isinstance(item, ScheduleBlockRow) for item in session.new)
            ):
                injected = True
                session.rollback()
                raise ConflictError("a concurrent or duplicate write was rejected")
            super().commit()

    def factory() -> SqlUnitOfWork:
        return RaceLosingUnitOfWork(session_factory)

    load_synthetic_fixtures(factory)
    service = PersonalOSService(
        uow_factory=factory,
        model_provider=DeterministicMockModelProvider(),
        calendar_provider=DeterministicMockCalendarProvider(),
    )
    captured = service.capture_intent(
        CaptureIntentCommand(
            user_id=DEMO_USER_ID,
            raw_text="I need a haircut before the wedding next month.",
            correlation_id="race-denial-capture-correlation",
            idempotency_key="race-denial-capture-0001",
        )
    )
    assert captured.proposal is not None

    with pytest.raises(ConflictError, match="concurrent or duplicate"):
        service.decide_proposal(
            DecideProposalCommand(
                user_id=DEMO_USER_ID,
                proposal_id=captured.proposal.id,
                decision=ProposalDecision.APPROVE,
                expected_version=captured.proposal.version,
                correlation_id="race-denial-approval-correlation",
                idempotency_key="race-denial-approval-0001",
            )
        )

    with factory() as uow:
        assert uow.blocks.list_for_user(DEMO_USER_ID) == []
        denied = [
            event
            for event in uow.audit.list_for_user(DEMO_USER_ID)
            if event.action == "schedule.decision_denied"
            and event.causation_id == "race-denial-approval-0001"
        ]
        assert len(denied) == 1
        assert denied[0].outcome == "denied"
        assert denied[0].policy_result == "denied:concurrent-or-duplicate-write"
