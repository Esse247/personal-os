from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from threading import Barrier
from time import perf_counter, sleep

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import Engine, delete, func, insert, select, text, update
from sqlalchemy.exc import DBAPIError, IntegrityError
from sqlalchemy.orm import sessionmaker

from personal_os.adapters.persistence.models import (
    ApprovalRow,
    AuditEventRow,
    CommandReceiptRow,
    ConsumerReceiptRow,
    FinancialTransactionRow,
    InternalEffectRow,
    OutboxEventRow,
    OutboxTransitionRow,
    ProjectRow,
    ScheduleBlockRow,
    WorldFactRow,
)
from personal_os.adapters.persistence.repositories import SqlUnitOfWork, create_uow_factory
from personal_os.adapters.providers.mock import (
    DeterministicMockCalendarProvider,
    DeterministicMockModelProvider,
)
from personal_os.application.commands import (
    CaptureIntentCommand,
    DecideProposalCommand,
    ProposalDecision,
    RecoverOutboxEventCommand,
)
from personal_os.application.policy import (
    AuthContext,
    FoundationPolicy,
    PolicyDecision,
    ResourceRef,
)
from personal_os.application.services import PersonalOSService
from personal_os.config import DEMO_USER_ID, OTHER_USER_ID, Settings
from personal_os.domain.entities import (
    BlockStatus,
    Commitment,
    CommitmentStatus,
    ProposalStatus,
    ScheduleBlock,
    ScheduleProposal,
)
from personal_os.domain.errors import AuthorizationError, ConflictError, LockTimeoutError
from personal_os.domain.events import (
    ConsumerReceipt,
    InternalEffect,
    InternalEventType,
    OutboxEvent,
    OutboxStatus,
    OutboxTransitionType,
)
from personal_os.domain.provenance import (
    ConfirmationStatus,
    Provenance,
    Sensitivity,
    SourceType,
)
from personal_os.fixtures import OTHER_TRANSACTION_ID, load_synthetic_fixtures
from personal_os.interfaces.http.app import create_app
from personal_os.ports.providers import ProviderRequestContext
from personal_os.ports.repositories import BlockRepository, UnitOfWork
from personal_os.worker import (
    InternalEventHandler,
    OutboxProcessor,
    RetryableExecutionError,
)


def provenance(user_id: str, correlation_id: str) -> Provenance:
    now = datetime(2026, 8, 10, 8, 0, tzinfo=UTC)
    return Provenance(
        source_type=SourceType.USER_STATED,
        source_identifier=f"postgresql-test:{correlation_id}",
        observed_at=now,
        recorded_at=now,
        confidence=1.0,
        confirmation_status=ConfirmationStatus.CONFIRMED,
        sensitivity=Sensitivity.PERSONAL,
        actor_id=user_id,
        data_subject_id=user_id,
        controller_id=user_id,
        correlation_id=correlation_id,
    )


def canonical_event(event_id: str, owner_user_id: str = DEMO_USER_ID) -> OutboxEvent:
    occurred_at = datetime(2026, 8, 10, 7, 0, tzinfo=UTC)
    return OutboxEvent(
        id=event_id,
        event_type=InternalEventType.INTENT_CAPTURED,
        schema_version=1,
        aggregate_type="intent",
        aggregate_id=f"aggregate-{event_id}",
        aggregate_version=1,
        owner_user_id=owner_user_id,
        controller_id=owner_user_id,
        data_subject_id=owner_user_id,
        actor_id=owner_user_id,
        on_behalf_of_id=None,
        sensitivity="personal",
        correlation_id=f"correlation-{event_id}",
        causation_id=f"causation-{event_id}",
        occurred_at=occurred_at,
        capability_mode="local-mock-synthetic",
        producer_key=f"producer-{event_id}",
        payload={"state": "captured"},
        available_at=occurred_at,
    )


def reset_postgresql_outbox(postgresql_engine: Engine) -> None:
    with postgresql_engine.begin() as connection:
        connection.execute(
            text(
                "TRUNCATE consumer_receipts, internal_effects, outbox_transitions, "
                "outbox_events CASCADE"
            )
        )


class PostgreSQLRetryHandler:
    consumer_name = "internal-redacted-projection-v1"
    mode = "internal-mock-only"
    action_level = 3

    def build_effect(
        self, event: OutboxEvent, *, effect_id: str, occurred_at: datetime
    ) -> InternalEffect:
        raise RetryableExecutionError("postgresql-transient")


class PostgreSQLRecoveryAllowedOncePolicy(FoundationPolicy):
    def __init__(self) -> None:
        super().__init__()
        self.recovery_decisions = 0

    def decide(
        self,
        context: AuthContext,
        permission: str,
        resource: ResourceRef,
    ) -> PolicyDecision:
        if permission == self.RECOVER_PERMISSION:
            self.recovery_decisions += 1
            allowed = self.recovery_decisions == 1
            return PolicyDecision(
                allowed,
                "initial-recovery-allowed" if allowed else "recovery-authority-revoked",
            )
        return super().decide(context, permission, resource)


def test_clean_migration_head_and_deterministic_fixtures(
    postgresql_engine: Engine,
) -> None:
    factory = create_uow_factory(postgresql_engine)
    load_synthetic_fixtures(factory)
    load_synthetic_fixtures(factory)
    with postgresql_engine.connect() as connection:
        assert connection.execute(text("SELECT version_num FROM alembic_version")).scalar_one() == (
            "0008_operator_receipts"
        )
        assert connection.execute(select(func.count(FinancialTransactionRow.id))).scalar_one() == 2
        assert connection.execute(select(func.count(AuditEventRow.id))).scalar_one() == 2
        assert connection.execute(text("SHOW TIME ZONE")).scalar_one() == "UTC"
        occurs_at = connection.execute(select(WorldFactRow.occurs_at)).scalar_one()
        assert occurs_at.tzinfo is not None


def test_postgresql_audit_rows_reject_update_and_delete(
    postgresql_engine: Engine,
) -> None:
    with pytest.raises(DBAPIError, match="append-only"), postgresql_engine.begin() as connection:
        connection.execute(
            update(AuditEventRow)
            .where(AuditEventRow.id == "audit-transaction-imported-001")
            .values(summary="mutated")
        )
    with pytest.raises(DBAPIError, match="append-only"), postgresql_engine.begin() as connection:
        connection.execute(
            delete(AuditEventRow).where(AuditEventRow.id == "audit-transaction-imported-001")
        )
    with postgresql_engine.connect() as connection:
        summary = connection.execute(
            select(AuditEventRow.summary).where(
                AuditEventRow.id == "audit-transaction-imported-001"
            )
        ).scalar_one()
    assert summary != "mutated"


def test_postgresql_constraint_failure_rolls_back_state_audit_and_receipt(
    postgresql_engine: Engine,
) -> None:
    now = datetime(2026, 8, 10, 9, 0, tzinfo=UTC)
    duplicate_key = "postgresql-rollback-receipt-0001"
    with postgresql_engine.begin() as connection:
        connection.execute(
            insert(CommandReceiptRow).values(
                idempotency_key=duplicate_key,
                user_id=DEMO_USER_ID,
                command_type="rollback_probe",
                request_digest="a" * 64,
                created_at=now,
            )
        )
    with pytest.raises(IntegrityError), postgresql_engine.begin() as connection:
        connection.execute(
            insert(ProjectRow).values(
                id="postgresql-rolled-back-project",
                user_id=DEMO_USER_ID,
                name="Rolled back",
                status="active",
                is_primary=False,
                created_at=now,
            )
        )
        connection.execute(
            insert(AuditEventRow).values(
                id="postgresql-rolled-back-audit",
                user_id=DEMO_USER_ID,
                action="postgresql.rollback_probe",
                entity_type="project",
                entity_id="postgresql-rolled-back-project",
                correlation_id="postgresql-rollback-correlation",
                occurred_at=now,
                outcome="succeeded",
                source_type=SourceType.USER_STATED.value,
                source_identifier="postgresql-test:rollback",
                actor_id=DEMO_USER_ID,
                on_behalf_of_id=None,
                entity_version=1,
                causation_id=duplicate_key,
                policy_result="allowed:test",
                capability_mode="local-mock-synthetic",
                approval_id=None,
                tool_reference=None,
                agent_reference=None,
                summary="Must roll back.",
                details_json="{}",
            )
        )
        connection.execute(
            insert(CommandReceiptRow).values(
                idempotency_key=duplicate_key,
                user_id=DEMO_USER_ID,
                command_type="rollback_probe",
                request_digest="b" * 64,
                created_at=now,
            )
        )
    with postgresql_engine.connect() as connection:
        assert (
            connection.execute(
                select(ProjectRow.id).where(ProjectRow.id == "postgresql-rolled-back-project")
            ).scalar_one_or_none()
            is None
        )
        assert (
            connection.execute(
                select(AuditEventRow.id).where(AuditEventRow.id == "postgresql-rolled-back-audit")
            ).scalar_one_or_none()
            is None
        )


def test_postgresql_optimistic_proposal_compare_and_swap(
    postgresql_engine: Engine,
) -> None:
    factory = create_uow_factory(postgresql_engine)
    service = PersonalOSService(
        uow_factory=factory,
        model_provider=DeterministicMockModelProvider(),
        calendar_provider=DeterministicMockCalendarProvider(),
    )
    captured = service.capture_intent(
        CaptureIntentCommand(
            user_id=DEMO_USER_ID,
            raw_text="I need a haircut before the wedding next month.",
            correlation_id="postgresql-cas-capture",
            idempotency_key="postgresql-cas-capture-0001",
        )
    )
    assert captured.proposal is not None
    proposal_id = captured.proposal.id
    barrier = Barrier(2)

    def reject_once() -> str:
        try:
            with factory() as uow:
                proposal = uow.proposals.get(proposal_id)
                assert proposal is not None
                barrier.wait(timeout=5)
                proposal.reject(proposal.version)
                uow.proposals.add(proposal)
                uow.commit()
            return "updated"
        except ConflictError:
            return "conflict"

    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = [pool.submit(reject_once) for _ in range(2)]
        outcomes = sorted(future.result() for future in futures)
    assert outcomes == ["conflict", "updated"]


def test_postgresql_advisory_lock_prevents_partial_overlap_race(
    postgresql_engine: Engine,
) -> None:
    factory = create_uow_factory(postgresql_engine)
    now = datetime(2026, 8, 10, 10, 0, tzinfo=UTC)
    user_id = "postgresql-overlap-user"
    with factory() as uow:
        for suffix in ("a", "b"):
            uow.commitments.add(
                Commitment(
                    id=f"postgresql-overlap-commitment-{suffix}",
                    user_id=user_id,
                    title=f"Overlap {suffix}",
                    status=CommitmentStatus.CAPTURED,
                    due_at=now + timedelta(days=2),
                    duration_minutes=60,
                    provenance=provenance(user_id, f"postgresql-overlap-{suffix}"),
                    created_at=now,
                )
            )
        uow.commit()
    barrier = Barrier(2)
    blocks = (
        ScheduleBlock(
            id="postgresql-overlap-block-a",
            user_id=user_id,
            commitment_id="postgresql-overlap-commitment-a",
            starts_at=now + timedelta(hours=1),
            ends_at=now + timedelta(hours=2),
            status=BlockStatus.CONFIRMED,
            created_at=now,
        ),
        ScheduleBlock(
            id="postgresql-overlap-block-b",
            user_id=user_id,
            commitment_id="postgresql-overlap-commitment-b",
            starts_at=now + timedelta(hours=1, minutes=30),
            ends_at=now + timedelta(hours=2, minutes=30),
            status=BlockStatus.CONFIRMED,
            created_at=now,
        ),
    )

    def add_block(block: ScheduleBlock) -> str:
        try:
            with factory() as uow:
                barrier.wait(timeout=5)
                uow.blocks.add(block)
                uow.commit()
            return "inserted"
        except ConflictError:
            return "conflict"

    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = [pool.submit(add_block, block) for block in blocks]
        outcomes = sorted(future.result() for future in futures)
    assert outcomes == ["conflict", "inserted"]
    with postgresql_engine.connect() as connection:
        count = connection.execute(
            select(func.count(ScheduleBlockRow.id)).where(ScheduleBlockRow.user_id == user_id)
        ).scalar_one()
    assert count == 1


def test_postgresql_partial_overlap_approval_race_keeps_one_block_and_denial_audit(
    postgresql_engine: Engine,
) -> None:
    factory = create_uow_factory(postgresql_engine)
    user_id = "postgresql-partial-overlap-user"
    now = datetime(2026, 8, 10, 8, 0, tzinfo=UTC)
    provider = DeterministicMockCalendarProvider()
    snapshot = provider.availability(
        user_id=user_id,
        before_iso=datetime(2026, 9, 19, tzinfo=UTC).isoformat(),
        context=ProviderRequestContext(
            actor_id="chief-of-staff-system",
            on_behalf_of_id=user_id,
            correlation_id="postgresql-overlap-snapshot",
            capability="calendar.availability.read.mock",
            purpose="construct a deterministic PostgreSQL race fixture",
            deadline_at=datetime(2026, 9, 19, tzinfo=UTC),
            idempotency_key="postgresql-overlap-snapshot-0001",
            task_type="scheduling",
            risk="low",
            privacy="personal",
        ),
    )
    base_service = PersonalOSService(
        uow_factory=factory,
        model_provider=DeterministicMockModelProvider(),
        calendar_provider=provider,
    )
    proposals: list[ScheduleProposal] = []
    with factory() as uow:
        for suffix, starts_at in (
            ("a", datetime(2026, 9, 10, 9, 15, tzinfo=UTC)),
            ("b", datetime(2026, 9, 10, 9, 45, tzinfo=UTC)),
        ):
            commitment = Commitment(
                id=f"postgresql-partial-commitment-{suffix}",
                user_id=user_id,
                title=f"Partial overlap {suffix}",
                status=CommitmentStatus.CAPTURED,
                due_at=datetime(2026, 9, 19, 14, 0, tzinfo=UTC),
                duration_minutes=60,
                provenance=provenance(user_id, f"postgresql-partial-{suffix}"),
                created_at=now,
            )
            proposal = ScheduleProposal(
                id=f"postgresql-partial-proposal-{suffix}",
                user_id=user_id,
                commitment_id=commitment.id,
                starts_at=starts_at,
                ends_at=starts_at + timedelta(hours=1),
                status=ProposalStatus.PROPOSED,
                rationale="Barrier-synchronised PostgreSQL partial-overlap fixture.",
                input_snapshot_hash="0" * 64,
                revision=1,
                created_at=now,
                provenance=provenance(user_id, f"postgresql-partial-proposal-{suffix}"),
                calendar_provider_id=snapshot.provider_id,
                calendar_snapshot_version=snapshot.version,
            )
            proposal.input_snapshot_hash = base_service._proposal_snapshot_hash(
                proposal, commitment, snapshot
            )
            uow.commitments.add(commitment)
            uow.proposals.add(proposal)
            proposals.append(proposal)
        uow.commit()

    block_barrier = Barrier(2)

    class BarrierBlockRepository:
        def __init__(self, delegate: BlockRepository) -> None:
            self.delegate = delegate

        def add(self, entity: ScheduleBlock) -> None:
            block_barrier.wait(timeout=10)
            self.delegate.add(entity)

        def list_for_user(self, user_id: str) -> list[ScheduleBlock]:
            return self.delegate.list_for_user(user_id)

    session_factory = sessionmaker(bind=postgresql_engine, expire_on_commit=False)

    class BarrierUnitOfWork(SqlUnitOfWork):
        def __enter__(self) -> UnitOfWork:
            super().__enter__()
            self.blocks = BarrierBlockRepository(self.blocks)
            return self

    def approval_factory() -> UnitOfWork:
        return BarrierUnitOfWork(session_factory)

    service = PersonalOSService(
        uow_factory=approval_factory,
        model_provider=DeterministicMockModelProvider(),
        calendar_provider=DeterministicMockCalendarProvider(),
    )

    def approve(proposal: ScheduleProposal, suffix: str) -> str:
        try:
            service.decide_proposal(
                DecideProposalCommand(
                    user_id=user_id,
                    proposal_id=proposal.id,
                    decision=ProposalDecision.APPROVE,
                    expected_version=proposal.version,
                    correlation_id=f"postgresql-partial-approval-{suffix}",
                    idempotency_key=f"postgresql-partial-approval-key-{suffix}",
                )
            )
            return "approved"
        except ConflictError:
            return "conflict"

    with ThreadPoolExecutor(max_workers=2) as pool:
        outcomes = sorted(
            future.result()
            for future in (
                pool.submit(approve, proposals[0], "a"),
                pool.submit(approve, proposals[1], "b"),
            )
        )
    assert outcomes == ["approved", "conflict"]
    with postgresql_engine.connect() as connection:
        assert (
            connection.execute(
                select(func.count(ScheduleBlockRow.id)).where(ScheduleBlockRow.user_id == user_id)
            ).scalar_one()
            == 1
        )
        denials = connection.execute(
            select(AuditEventRow.policy_result).where(
                AuditEventRow.user_id == user_id,
                AuditEventRow.action == "schedule.decision_denied",
            )
        ).scalars()
        assert list(denials) == ["denied:concurrent-or-duplicate-write"]


def test_postgresql_skip_locked_claim_restart_delivery_and_immutable_history(
    postgresql_engine: Engine,
) -> None:
    reset_postgresql_outbox(postgresql_engine)
    factory = create_uow_factory(postgresql_engine)
    event_id = "postgresql-outbox-race-event"
    with factory() as uow:
        uow.outbox.enqueue(canonical_event(event_id))
        uow.commit()
    start = Barrier(2)
    claimed = Barrier(2)

    def claim(worker: str) -> str | None:
        with factory() as uow:
            start.wait(timeout=10)
            event = uow.outbox.claim_next(worker, 30)
            claimed.wait(timeout=10)
            if event is not None:
                uow.commit()
                return event.lease_token
            return None

    with ThreadPoolExecutor(max_workers=2) as pool:
        tokens = [
            future.result()
            for future in (
                pool.submit(claim, "personal-os-worker:pg-a"),
                pool.submit(claim, "personal-os-worker:pg-b"),
            )
        ]
    winning_tokens = [token for token in tokens if token is not None]
    assert len(winning_tokens) == 1
    with postgresql_engine.begin() as connection:
        connection.execute(
            text(
                "UPDATE outbox_events SET lease_expires_at = CURRENT_TIMESTAMP - "
                "INTERVAL '1 second' WHERE id = :event_id"
            ),
            {"event_id": event_id},
        )
    result = OutboxProcessor(
        uow_factory=factory,
        environment="test",
        instance_id="pg-restart",
    ).process_one()
    assert result.event_id == event_id
    assert result.status == "delivered"
    with postgresql_engine.connect() as connection:
        transitions = connection.execute(
            select(OutboxTransitionRow.transition, OutboxTransitionRow.policy_result)
            .where(OutboxTransitionRow.event_id == event_id)
            .order_by(OutboxTransitionRow.sequence)
        ).all()
        assert transitions == [
            (
                OutboxTransitionType.CLAIMED.value,
                "preauthorization:execution-claim-v1",
            ),
            (
                OutboxTransitionType.RECLAIMED.value,
                "preauthorization:execution-claim-v1",
            ),
            (
                OutboxTransitionType.DELIVERED.value,
                "allowed:execution-delivery-v1",
            ),
        ]
        assert (
            connection.execute(
                select(func.count(InternalEffectRow.id)).where(
                    InternalEffectRow.event_id == event_id
                )
            ).scalar_one()
            == 1
        )
        assert (
            connection.execute(
                select(func.count(ConsumerReceiptRow.event_id)).where(
                    ConsumerReceiptRow.event_id == event_id
                )
            ).scalar_one()
            == 1
        )
    with postgresql_engine.begin() as connection:
        connection.execute(
            text(
                "UPDATE outbox_events SET status = 'pending', available_at = CURRENT_TIMESTAMP, "
                "attempt_count = 0, delivered_at = NULL WHERE id = :event_id"
            ),
            {"event_id": event_id},
        )
    duplicate = OutboxProcessor(
        uow_factory=factory,
        environment="test",
        instance_id="pg-duplicate",
    ).process_one()
    assert duplicate.event_id == event_id
    assert duplicate.status == "delivered"
    with postgresql_engine.connect() as connection:
        assert (
            connection.execute(
                select(func.count(InternalEffectRow.id)).where(
                    InternalEffectRow.event_id == event_id
                )
            ).scalar_one()
            == 1
        )
        assert (
            connection.execute(
                select(func.count(ConsumerReceiptRow.event_id)).where(
                    ConsumerReceiptRow.event_id == event_id
                )
            ).scalar_one()
            == 1
        )
        assert (
            connection.execute(
                select(OutboxTransitionRow.transition)
                .where(OutboxTransitionRow.event_id == event_id)
                .order_by(OutboxTransitionRow.sequence.desc())
                .limit(1)
            ).scalar_one()
            == OutboxTransitionType.DUPLICATE_SUPPRESSED.value
        )
    with pytest.raises(DBAPIError, match="append-only"), postgresql_engine.begin() as connection:
        connection.execute(
            update(OutboxTransitionRow)
            .where(OutboxTransitionRow.event_id == event_id)
            .values(policy_result="mutated")
        )


def test_postgresql_stale_fencing_token_rolls_back_effect_and_receipt(
    postgresql_engine: Engine,
) -> None:
    reset_postgresql_outbox(postgresql_engine)
    factory = create_uow_factory(postgresql_engine)
    event_id = "postgresql-stale-fence-event"
    with factory() as uow:
        uow.outbox.enqueue(canonical_event(event_id))
        uow.commit()
    with factory() as uow:
        claim = uow.outbox.claim_next("personal-os-worker:pg-old", 30)
        assert claim is not None and claim.lease_token is not None
        old_token = claim.lease_token
        uow.commit()
    with postgresql_engine.begin() as connection:
        connection.execute(
            text(
                "UPDATE outbox_events SET lease_owner = 'personal-os-worker:pg-new', "
                "lease_token = 'postgresql-new-fencing-token', "
                "lease_expires_at = CURRENT_TIMESTAMP + INTERVAL '1 minute' "
                "WHERE id = :event_id"
            ),
            {"event_id": event_id},
        )
    occurred_at = datetime(2026, 8, 10, 8, 0, tzinfo=UTC)
    with factory() as uow:
        effect = InternalEffect(
            id="postgresql-stale-effect",
            consumer_name="internal-redacted-projection-v1",
            event_id=event_id,
            owner_user_id=DEMO_USER_ID,
            effect_type="internal.redacted_event_projection.v1",
            occurred_at=occurred_at,
            payload={
                "event_type": InternalEventType.INTENT_CAPTURED.value,
                "aggregate_type": "intent",
                "state": "captured",
            },
        )
        uow.internal_effects.add(effect)
        uow.consumer_receipts.add(
            ConsumerReceipt(
                consumer_name=effect.consumer_name,
                event_id=event_id,
                effect_id=effect.id,
                processed_at=occurred_at,
            )
        )
        with pytest.raises(ConflictError, match="stale"):
            uow.outbox.mark_delivered(
                event_id,
                "personal-os-worker:pg-old",
                old_token,
            )
    with postgresql_engine.connect() as connection:
        assert (
            connection.execute(
                select(func.count(InternalEffectRow.id)).where(
                    InternalEffectRow.event_id == event_id
                )
            ).scalar_one()
            == 0
        )
        assert (
            connection.execute(
                select(func.count(ConsumerReceiptRow.event_id)).where(
                    ConsumerReceiptRow.event_id == event_id
                )
            ).scalar_one()
            == 0
        )


@pytest.mark.parametrize("operation", ["deliver", "failure"])
def test_postgresql_wall_clock_expiry_rejects_a_transaction_started_while_lease_valid(
    postgresql_engine: Engine,
    operation: str,
) -> None:
    reset_postgresql_outbox(postgresql_engine)
    factory = create_uow_factory(postgresql_engine)
    event_id = f"postgresql-wall-clock-expiry-{operation}"
    worker = f"personal-os-worker:pg-expiry-{operation}"
    with factory() as uow:
        uow.outbox.enqueue(canonical_event(event_id))
        uow.commit()
    with factory() as uow:
        claim = uow.outbox.claim_next(worker, 30)
        assert claim is not None and claim.lease_token is not None
        lease_token = claim.lease_token
        uow.commit()
    # The read starts the transaction while the lease is still valid. PostgreSQL's
    # CURRENT_TIMESTAMP would remain frozen at this point and incorrectly permit the
    # later update; the fenced statement must instead compare with clock_timestamp().
    with factory() as uow:
        observed = uow.outbox.get(event_id)
        assert observed is not None
        with postgresql_engine.begin() as connection:
            connection.execute(
                text(
                    "UPDATE outbox_events SET lease_expires_at = "
                    "clock_timestamp() + INTERVAL '500 milliseconds' "
                    "WHERE id = :event_id"
                ),
                {"event_id": event_id},
            )
        # The tested transaction definitely predates the new future expiry, then remains
        # open until wall-clock time has passed it.
        sleep(0.8)
        occurred_at = datetime.now(UTC)
        effect = InternalEffect(
            id=f"postgresql-expired-effect-{operation}",
            consumer_name="internal-redacted-projection-v1",
            event_id=event_id,
            owner_user_id=DEMO_USER_ID,
            effect_type="internal.redacted_event_projection.v1",
            occurred_at=occurred_at,
            payload={
                "event_type": InternalEventType.INTENT_CAPTURED.value,
                "aggregate_type": "intent",
                "state": "captured",
            },
        )
        uow.internal_effects.add(effect)
        uow.consumer_receipts.add(
            ConsumerReceipt(
                consumer_name=effect.consumer_name,
                event_id=event_id,
                effect_id=effect.id,
                processed_at=occurred_at,
            )
        )
        with pytest.raises(ConflictError, match="stale"):
            if operation == "deliver":
                uow.outbox.mark_delivered(event_id, worker, lease_token)
            else:
                uow.outbox.record_failure(
                    event_id,
                    worker,
                    lease_token,
                    "postgresql-expired-lease",
                    retryable=True,
                    policy_result="denied:expired-lease-test",
                )

    with postgresql_engine.connect() as connection:
        state = connection.execute(
            text("SELECT status, lease_token FROM outbox_events WHERE id = :event_id"),
            {"event_id": event_id},
        ).one()
        assert state == (OutboxStatus.PROCESSING.value, lease_token)
        assert (
            connection.execute(
                select(func.count(InternalEffectRow.id)).where(
                    InternalEffectRow.event_id == event_id
                )
            ).scalar_one()
            == 0
        )
        assert (
            connection.execute(
                select(func.count(ConsumerReceiptRow.event_id)).where(
                    ConsumerReceiptRow.event_id == event_id
                )
            ).scalar_one()
            == 0
        )


def test_postgresql_retry_exhaustion_visibility_and_owner_recovery(
    postgresql_engine: Engine,
) -> None:
    reset_postgresql_outbox(postgresql_engine)
    factory = create_uow_factory(postgresql_engine)
    event_id = "postgresql-retry-recovery-event"
    with factory() as uow:
        uow.outbox.enqueue(canonical_event(event_id))
        uow.commit()
    handler: InternalEventHandler = PostgreSQLRetryHandler()
    processor = OutboxProcessor(
        uow_factory=factory,
        handlers={event_type: handler for event_type in InternalEventType},
        environment="test",
        instance_id="pg-retry",
    )
    for attempt in range(3):
        result = processor.process_one()
        assert result.event_id == event_id
        if attempt < 2:
            assert result.status == OutboxStatus.RETRY.value
            with postgresql_engine.begin() as connection:
                connection.execute(
                    text(
                        "UPDATE outbox_events SET available_at = CURRENT_TIMESTAMP - "
                        "INTERVAL '1 second' WHERE id = :event_id"
                    ),
                    {"event_id": event_id},
                )
        else:
            assert result.status == OutboxStatus.FAILED.value
    assert [
        event.id
        for event in processor.failed_for_owner(actor_id=DEMO_USER_ID, owner_user_id=DEMO_USER_ID)
    ] == [event_id]
    with pytest.raises(AuthorizationError):
        processor.recover_failed(
            RecoverOutboxEventCommand(
                user_id=OTHER_USER_ID,
                event_id=event_id,
                reason="Cross-person recovery must fail.",
                correlation_id="postgresql-cross-person-recovery",
                idempotency_key="postgresql-cross-person-recovery-0001",
            )
        )
    recovered = processor.recover_failed(
        RecoverOutboxEventCommand(
            user_id=DEMO_USER_ID,
            event_id=event_id,
            reason="Retry after explicit synthetic operator review.",
            correlation_id="postgresql-recovery-correlation",
            idempotency_key="postgresql-recovery-idempotency-0001",
        )
    )
    assert recovered.status is OutboxStatus.PENDING
    assert recovered.attempt_count == 0
    assert recovered.cycle == 1
    with postgresql_engine.connect() as connection:
        transitions = list(
            connection.execute(
                select(OutboxTransitionRow.transition)
                .where(OutboxTransitionRow.event_id == event_id)
                .order_by(OutboxTransitionRow.sequence)
            ).scalars()
        )
    assert transitions.count(OutboxTransitionType.RETRY_SCHEDULED.value) == 2
    assert transitions[-2:] == [
        OutboxTransitionType.FAILED.value,
        OutboxTransitionType.RECOVERED.value,
    ]


def test_postgresql_concurrent_exact_recovery_replays_one_durable_result(
    postgresql_engine: Engine,
) -> None:
    reset_postgresql_outbox(postgresql_engine)
    factory = create_uow_factory(postgresql_engine)
    event_id = "postgresql-concurrent-recovery-event"
    with factory() as uow:
        uow.outbox.enqueue(
            replace(
                canonical_event(event_id),
                status=OutboxStatus.FAILED,
                attempt_count=3,
                last_failure_code="postgresql-terminal",
            )
        )
        uow.commit()
    command = RecoverOutboxEventCommand(
        user_id=DEMO_USER_ID,
        event_id=event_id,
        reason="Retry once after concurrent operator delivery.",
        correlation_id="postgresql-concurrent-recovery",
        idempotency_key="postgresql-concurrent-recovery-0001",
    )
    barrier = Barrier(2)

    def recover() -> object:
        barrier.wait()
        return OutboxProcessor(
            uow_factory=factory,
            environment="test",
            instance_id="pg-concurrent-recovery",
        ).recover_failed(command)

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda _: recover(), range(2)))
    assert results[0] == results[1]
    with postgresql_engine.connect() as connection:
        assert (
            connection.execute(
                select(func.count(CommandReceiptRow.idempotency_key)).where(
                    CommandReceiptRow.idempotency_key == command.idempotency_key
                )
            ).scalar_one()
            == 1
        )
        assert (
            connection.execute(
                select(func.count(OutboxTransitionRow.id)).where(
                    OutboxTransitionRow.event_id == event_id,
                    OutboxTransitionRow.transition == OutboxTransitionType.RECOVERED.value,
                )
            ).scalar_one()
            == 1
        )
        assert (
            connection.execute(
                select(func.count(OutboxTransitionRow.id)).where(
                    OutboxTransitionRow.event_id == event_id,
                    OutboxTransitionRow.transition == OutboxTransitionType.RECOVERED.value,
                )
            ).scalar_one()
            == 1
        )


def test_postgresql_exact_recovery_replay_reauthorizes_before_disclosure(
    postgresql_engine: Engine,
) -> None:
    reset_postgresql_outbox(postgresql_engine)
    factory = create_uow_factory(postgresql_engine)
    event_id = "postgresql-recovery-reauthorization-event"
    with factory() as uow:
        uow.outbox.enqueue(
            replace(
                canonical_event(event_id),
                status=OutboxStatus.FAILED,
                attempt_count=3,
                last_failure_code="postgresql-terminal",
            )
        )
        uow.commit()

    policy = PostgreSQLRecoveryAllowedOncePolicy()
    processor = OutboxProcessor(
        uow_factory=factory,
        policy=policy,
        environment="test",
        instance_id="pg-recovery-reauth",
    )
    reason = "Retry once while PostgreSQL recovery authority remains active."
    idempotency_key = "postgresql-recovery-reauthorization-0001"
    recovered = processor.recover_failed(
        RecoverOutboxEventCommand(
            user_id=DEMO_USER_ID,
            event_id=event_id,
            reason=reason,
            correlation_id="postgresql-recovery-reauthorization-initial",
            idempotency_key=idempotency_key,
        )
    )
    assert recovered.status is OutboxStatus.PENDING

    with pytest.raises(AuthorizationError, match="resource not found"):
        processor.recover_failed(
            RecoverOutboxEventCommand(
                user_id=DEMO_USER_ID,
                event_id=event_id,
                reason=reason,
                correlation_id="postgresql-recovery-reauthorization-replay-denied",
                idempotency_key=idempotency_key,
            )
        )

    assert policy.recovery_decisions == 2
    with postgresql_engine.connect() as connection:
        assert (
            connection.execute(
                select(func.count(CommandReceiptRow.idempotency_key)).where(
                    CommandReceiptRow.idempotency_key == idempotency_key
                )
            ).scalar_one()
            == 1
        )
        assert (
            connection.execute(
                select(func.count(OutboxTransitionRow.id)).where(
                    OutboxTransitionRow.event_id == event_id,
                    OutboxTransitionRow.transition == OutboxTransitionType.RECOVERED.value,
                )
            ).scalar_one()
            == 1
        )
        denied_audit = connection.execute(
            select(AuditEventRow.correlation_id, AuditEventRow.policy_result).where(
                AuditEventRow.action == "execution.recovery_denied",
                AuditEventRow.entity_id == event_id,
            )
        ).one()
    assert denied_audit == (
        "postgresql-recovery-reauthorization-replay-denied",
        "denied:recovery-authority-revoked",
    )


def test_postgresql_recovery_lock_timeout_is_bounded_audited_and_retryable(
    postgresql_engine: Engine,
) -> None:
    reset_postgresql_outbox(postgresql_engine)
    factory = create_uow_factory(postgresql_engine)
    event_id = "postgresql-recovery-lock-timeout-event"
    with factory() as uow:
        uow.outbox.enqueue(
            replace(
                canonical_event(event_id),
                status=OutboxStatus.FAILED,
                attempt_count=3,
                last_failure_code="postgresql-terminal",
            )
        )
        uow.commit()

    command = RecoverOutboxEventCommand(
        user_id=DEMO_USER_ID,
        event_id=event_id,
        reason="Retry after the competing synthetic operator releases the key.",
        correlation_id="postgresql-recovery-lock-timeout",
        idempotency_key="postgresql-recovery-lock-timeout-0001",
    )
    processor = OutboxProcessor(
        uow_factory=factory,
        environment="test",
        instance_id="pg-recovery-lock-timeout",
    )

    with postgresql_engine.connect() as holder:
        transaction = holder.begin()
        holder.execute(
            select(func.pg_advisory_xact_lock(func.hashtextextended(command.idempotency_key, 1)))
        )
        started_at = perf_counter()
        with pytest.raises(LockTimeoutError, match="temporarily busy"):
            processor.recover_failed(command)
        elapsed = perf_counter() - started_at
        transaction.rollback()

    assert 0.4 <= elapsed < 2.0
    with postgresql_engine.connect() as connection:
        assert (
            connection.execute(
                select(func.count(CommandReceiptRow.idempotency_key)).where(
                    CommandReceiptRow.idempotency_key == command.idempotency_key
                )
            ).scalar_one()
            == 0
        )
        assert (
            connection.execute(
                select(func.count(OutboxTransitionRow.id)).where(
                    OutboxTransitionRow.event_id == event_id,
                    OutboxTransitionRow.transition == OutboxTransitionType.RECOVERED.value,
                )
            ).scalar_one()
            == 0
        )
        assert (
            connection.execute(
                select(OutboxEventRow.status).where(OutboxEventRow.id == event_id)
            ).scalar_one()
            == OutboxStatus.FAILED.value
        )
        timeout_audit = connection.execute(
            select(
                AuditEventRow.action,
                AuditEventRow.outcome,
                AuditEventRow.correlation_id,
                AuditEventRow.policy_result,
                AuditEventRow.details_json,
            ).where(
                AuditEventRow.entity_id == event_id,
                AuditEventRow.action == "execution.recovery_deferred",
            )
        ).one()
    assert timeout_audit.action == "execution.recovery_deferred"
    assert timeout_audit.outcome == "failed"
    assert timeout_audit.correlation_id == command.correlation_id
    assert timeout_audit.policy_result == "allowed:execution-owner-recovery-v1"
    assert '"failure_code": "recovery-lock-timeout"' in timeout_audit.details_json

    recovered = processor.recover_failed(command)
    assert recovered.status is OutboxStatus.PENDING
    assert recovered.cycle == 1
    with postgresql_engine.connect() as connection:
        assert (
            connection.execute(
                select(func.count(CommandReceiptRow.idempotency_key)).where(
                    CommandReceiptRow.idempotency_key == command.idempotency_key
                )
            ).scalar_one()
            == 1
        )
        assert (
            connection.execute(
                select(func.count(OutboxTransitionRow.id)).where(
                    OutboxTransitionRow.event_id == event_id,
                    OutboxTransitionRow.transition == OutboxTransitionType.RECOVERED.value,
                )
            ).scalar_one()
            == 1
        )


def test_postgresql_recovery_lock_timeout_scope_is_restored_after_success(
    postgresql_engine: Engine,
) -> None:
    session_factory = sessionmaker(bind=postgresql_engine, expire_on_commit=False)
    uow = SqlUnitOfWork(session_factory)
    with uow:
        assert uow.session is not None
        uow.session.scalar(select(func.set_config("lock_timeout", "2s", True)))
        assert uow.session.scalar(select(func.current_setting("lock_timeout"))) == "2s"

        uow.receipts.lock_key("postgresql-recovery-lock-timeout-scope-0001")

        assert uow.session.scalar(select(func.current_setting("lock_timeout"))) == "2s"


def test_postgresql_recovery_row_lock_timeout_is_bounded_audited_and_retryable(
    postgresql_engine: Engine,
) -> None:
    reset_postgresql_outbox(postgresql_engine)
    factory = create_uow_factory(postgresql_engine)
    event_id = "postgresql-recovery-row-lock-timeout-event"
    with factory() as uow:
        uow.outbox.enqueue(
            replace(
                canonical_event(event_id),
                status=OutboxStatus.FAILED,
                attempt_count=3,
                last_failure_code="postgresql-terminal",
            )
        )
        uow.commit()

    command = RecoverOutboxEventCommand(
        user_id=DEMO_USER_ID,
        event_id=event_id,
        reason="Retry after the competing synthetic operator releases the event row.",
        correlation_id="postgresql-recovery-row-lock-timeout",
        idempotency_key="postgresql-recovery-row-lock-timeout-0001",
    )
    processor = OutboxProcessor(
        uow_factory=factory,
        environment="test",
        instance_id="pg-recovery-row-lock-timeout",
    )

    with postgresql_engine.connect() as holder:
        transaction = holder.begin()
        holder.execute(
            select(OutboxEventRow).where(OutboxEventRow.id == event_id).with_for_update()
        )
        started_at = perf_counter()
        with pytest.raises(LockTimeoutError, match="temporarily busy"):
            processor.recover_failed(command)
        elapsed = perf_counter() - started_at
        transaction.rollback()

    assert 0.4 <= elapsed < 2.0
    with postgresql_engine.connect() as connection:
        assert (
            connection.execute(
                select(func.count(CommandReceiptRow.idempotency_key)).where(
                    CommandReceiptRow.idempotency_key == command.idempotency_key
                )
            ).scalar_one()
            == 0
        )
        assert (
            connection.execute(
                select(func.count(OutboxTransitionRow.id)).where(
                    OutboxTransitionRow.event_id == event_id,
                    OutboxTransitionRow.transition == OutboxTransitionType.RECOVERED.value,
                )
            ).scalar_one()
            == 0
        )
        assert (
            connection.execute(
                select(OutboxEventRow.status).where(OutboxEventRow.id == event_id)
            ).scalar_one()
            == OutboxStatus.FAILED.value
        )
        timeout_audit = connection.execute(
            select(
                AuditEventRow.action,
                AuditEventRow.outcome,
                AuditEventRow.correlation_id,
                AuditEventRow.policy_result,
                AuditEventRow.details_json,
            ).where(
                AuditEventRow.entity_id == event_id,
                AuditEventRow.action == "execution.recovery_deferred",
                AuditEventRow.correlation_id == command.correlation_id,
            )
        ).one()
    assert timeout_audit.action == "execution.recovery_deferred"
    assert timeout_audit.outcome == "failed"
    assert timeout_audit.correlation_id == command.correlation_id
    assert timeout_audit.policy_result == "allowed:execution-owner-recovery-v1"
    assert '"failure_code": "recovery-lock-timeout"' in timeout_audit.details_json

    recovered = processor.recover_failed(command)
    assert recovered.status is OutboxStatus.PENDING
    assert recovered.cycle == 1
    with postgresql_engine.connect() as connection:
        assert (
            connection.execute(
                select(func.count(CommandReceiptRow.idempotency_key)).where(
                    CommandReceiptRow.idempotency_key == command.idempotency_key
                )
            ).scalar_one()
            == 1
        )
        assert (
            connection.execute(
                select(func.count(OutboxTransitionRow.id)).where(
                    OutboxTransitionRow.event_id == event_id,
                    OutboxTransitionRow.transition == OutboxTransitionType.RECOVERED.value,
                )
            ).scalar_one()
            == 1
        )


def test_postgresql_recovery_lock_timeout_does_not_disclose_to_wrong_actor(
    postgresql_engine: Engine,
) -> None:
    reset_postgresql_outbox(postgresql_engine)
    factory = create_uow_factory(postgresql_engine)
    event_id = "postgresql-recovery-lock-timeout-private-event"
    with factory() as uow:
        uow.outbox.enqueue(
            replace(
                canonical_event(event_id),
                status=OutboxStatus.FAILED,
                attempt_count=3,
                last_failure_code="postgresql-terminal",
            )
        )
        uow.commit()

    command = RecoverOutboxEventCommand(
        user_id=OTHER_USER_ID,
        event_id=event_id,
        reason="A different person must not learn whether recovery is busy.",
        correlation_id="postgresql-recovery-lock-timeout-private",
        idempotency_key="postgresql-recovery-lock-timeout-private-0001",
    )
    processor = OutboxProcessor(
        uow_factory=factory,
        environment="test",
        instance_id="pg-recovery-lock-timeout-private",
    )

    with postgresql_engine.connect() as holder:
        transaction = holder.begin()
        holder.execute(
            select(func.pg_advisory_xact_lock(func.hashtextextended(command.idempotency_key, 1)))
        )
        with pytest.raises(AuthorizationError, match="resource not found"):
            processor.recover_failed(command)
        transaction.rollback()

    with postgresql_engine.connect() as connection:
        assert (
            connection.execute(
                select(func.count(CommandReceiptRow.idempotency_key)).where(
                    CommandReceiptRow.idempotency_key == command.idempotency_key
                )
            ).scalar_one()
            == 0
        )
        assert (
            connection.execute(
                select(func.count(OutboxTransitionRow.id)).where(
                    OutboxTransitionRow.event_id == event_id,
                    OutboxTransitionRow.transition == OutboxTransitionType.RECOVERED.value,
                )
            ).scalar_one()
            == 0
        )
        denied_audit = connection.execute(
            select(AuditEventRow.correlation_id, AuditEventRow.policy_result).where(
                AuditEventRow.entity_id == event_id,
                AuditEventRow.action == "execution.recovery_denied",
            )
        ).one()
    assert denied_audit == (
        command.correlation_id,
        "denied:default-deny-recovery-scope",
    )


def test_postgresql_api_preserves_authorization_provenance_approval_and_idempotency(
    postgresql_engine: Engine,
) -> None:
    settings = Settings(
        environment="test",
        database_url=postgresql_engine.url.render_as_string(hide_password=False),
        auto_initialize=False,
    )
    with TestClient(create_app(settings, engine=postgresql_engine)) as client:
        headers = {"Idempotency-Key": "postgresql-api-capture-0001"}
        body = {"text": "I need a haircut before the wedding next month."}
        first = client.post("/v1/intents", json=body, headers=headers)
        replay = client.post("/v1/intents", json=body, headers=headers)
        mutated = client.post("/v1/intents", json={"text": "changed"}, headers=headers)
        assert first.status_code == replay.status_code == 201
        assert first.json()["intent"]["id"] == replay.json()["intent"]["id"]
        assert mutated.status_code == 409
        assert client.get(f"/v1/finance/transactions/{OTHER_TRANSACTION_ID}").status_code == 404

        proposal = first.json()["proposal"]
        decision_headers = {
            "Idempotency-Key": "postgresql-api-approval-0001",
            "If-Match": str(proposal["version"]),
        }
        approved = client.post(
            f"/v1/schedule-proposals/{proposal['id']}/decisions",
            json={"decision": "approve"},
            headers=decision_headers,
        )
        decision_replay = client.post(
            f"/v1/schedule-proposals/{proposal['id']}/decisions",
            json={"decision": "approve"},
            headers=decision_headers,
        )
        decision_mutation = client.post(
            f"/v1/schedule-proposals/{proposal['id']}/decisions",
            json={"decision": "reject"},
            headers=decision_headers,
        )
        assert approved.status_code == decision_replay.status_code == 200
        assert decision_mutation.status_code == 409

    with postgresql_engine.connect() as connection:
        approvals = connection.execute(
            select(ApprovalRow.id).where(
                ApprovalRow.idempotency_key == "postgresql-api-approval-0001"
            )
        ).all()
        assert len(approvals) == 1
        provenance_json = connection.execute(
            select(WorldFactRow.provenance_json).where(WorldFactRow.user_id == DEMO_USER_ID)
        ).scalar_one()
        assert '"data_subject_id": "user-alex-synthetic"' in provenance_json
        assert (
            connection.execute(
                select(func.count(AuditEventRow.id)).where(
                    AuditEventRow.correlation_id == first.headers["X-Correlation-ID"]
                )
            ).scalar_one()
            >= 1
        )
        assert (
            connection.execute(
                select(func.count(FinancialTransactionRow.id)).where(
                    FinancialTransactionRow.user_id == OTHER_USER_ID
                )
            ).scalar_one()
            == 1
        )
