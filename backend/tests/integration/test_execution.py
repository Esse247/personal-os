from __future__ import annotations

from collections.abc import Iterator
from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import Engine, func, select, update

from personal_os.adapters.persistence.database import initialize_schema
from personal_os.adapters.persistence.models import (
    AuditEventRow,
    CommandReceiptRow,
    ConsumerReceiptRow,
    IntentRow,
    InternalEffectRow,
    OutboxEventRow,
    OutboxTransitionRow,
)
from personal_os.adapters.persistence.repositories import create_uow_factory
from personal_os.adapters.providers.mock import (
    DeterministicMockCalendarProvider,
    DeterministicMockModelProvider,
)
from personal_os.application.commands import (
    CaptureIntentCommand,
    RecoverOutboxEventCommand,
)
from personal_os.application.policy import (
    AuthContext,
    FoundationPolicy,
    PolicyDecision,
    ResourceRef,
)
from personal_os.application.services import PersonalOSService
from personal_os.config import DEMO_USER_ID, OTHER_USER_ID
from personal_os.domain.errors import (
    AuthorizationError,
    ConflictError,
    ProhibitedCapabilityError,
)
from personal_os.domain.events import (
    ConsumerReceipt,
    InternalEffect,
    InternalEventType,
    OutboxEvent,
    OutboxStatus,
    OutboxTransitionType,
)
from personal_os.fixtures import load_synthetic_fixtures
from personal_os.worker import (
    InternalEventHandler,
    OutboxProcessor,
    RetryableExecutionError,
)


def id_sequence() -> Iterator[str]:
    number = 0
    while True:
        number += 1
        yield f"execution-test-id-{number:04d}"


def seed_application_events(engine: Engine) -> None:
    initialize_schema(engine)
    factory = create_uow_factory(engine)
    load_synthetic_fixtures(factory)
    PersonalOSService(
        uow_factory=factory,
        model_provider=DeterministicMockModelProvider(),
        calendar_provider=DeterministicMockCalendarProvider(),
    ).capture_intent(
        CaptureIntentCommand(
            user_id=DEMO_USER_ID,
            raw_text="I need a haircut before the wedding next month.",
            correlation_id="execution-capture-correlation",
            idempotency_key="execution-capture-idempotency-0001",
        )
    )


def first_event_id(engine: Engine) -> str:
    with engine.connect() as connection:
        return connection.execute(
            select(OutboxEventRow.id)
            .order_by(
                OutboxEventRow.available_at,
                OutboxEventRow.occurred_at,
                OutboxEventRow.id,
            )
            .limit(1)
        ).scalar_one()


class AlwaysRetryHandler:
    consumer_name = "internal-redacted-projection-v1"
    mode = "internal-mock-only"
    action_level = 3

    def build_effect(
        self, event: OutboxEvent, *, effect_id: str, occurred_at: datetime
    ) -> InternalEffect:
        raise RetryableExecutionError("synthetic-transient")


class RevokedBeforeEffectPolicy(FoundationPolicy):
    def __init__(self) -> None:
        super().__init__()
        self.handle_decisions = 0

    def decide(
        self,
        context: AuthContext,
        permission: str,
        resource: ResourceRef,
    ) -> PolicyDecision:
        if permission == self.HANDLE_PERMISSION:
            self.handle_decisions += 1
            return PolicyDecision(
                self.handle_decisions == 1,
                "first-check-only" if self.handle_decisions == 1 else "authority-revoked",
            )
        return super().decide(context, permission, resource)


class RecoveryAllowedOncePolicy(FoundationPolicy):
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


def test_authoritative_mutation_audit_receipt_and_outbox_commit_together(
    engine: Engine,
) -> None:
    initialize_schema(engine)
    factory = create_uow_factory(engine)
    load_synthetic_fixtures(factory)
    command = CaptureIntentCommand(
        user_id=DEMO_USER_ID,
        raw_text="I need a haircut before the wedding next month.",
        correlation_id="execution-atomic-correlation",
        idempotency_key="execution-atomic-idempotency-0001",
    )
    event_key = PersonalOSService._digest(
        {
            "event_type": InternalEventType.INTENT_CAPTURED.value,
            "aggregate_type": "intent",
            "aggregate_id": "execution-test-id-0001",
            "aggregate_version": 1,
            "causation_id": command.idempotency_key,
        }
    )
    now = datetime(2026, 8, 10, 12, 0, tzinfo=UTC)
    with factory() as uow:
        uow.outbox.enqueue(
            OutboxEvent(
                id="preexisting-outbox-event",
                event_type=InternalEventType.INTENT_CAPTURED,
                schema_version=1,
                aggregate_type="intent",
                aggregate_id="preexisting-intent",
                aggregate_version=1,
                owner_user_id=DEMO_USER_ID,
                controller_id=DEMO_USER_ID,
                data_subject_id=DEMO_USER_ID,
                actor_id=DEMO_USER_ID,
                on_behalf_of_id=None,
                sensitivity="personal",
                correlation_id="preexisting-correlation",
                causation_id="preexisting-causation",
                occurred_at=now,
                capability_mode="local-mock-synthetic",
                producer_key=event_key,
                payload={"state": "captured"},
                available_at=now,
            )
        )
        uow.commit()
    identifiers = id_sequence()
    service = PersonalOSService(
        uow_factory=factory,
        model_provider=DeterministicMockModelProvider(),
        calendar_provider=DeterministicMockCalendarProvider(),
        id_factory=lambda: next(identifiers),
    )
    with pytest.raises(ConflictError, match="concurrent or duplicate"):
        service.capture_intent(command)
    with engine.connect() as connection:
        assert (
            connection.execute(
                select(IntentRow.id).where(IntentRow.id == "execution-test-id-0001")
            ).scalar_one_or_none()
            is None
        )
        assert (
            connection.execute(
                select(AuditEventRow.id).where(
                    AuditEventRow.correlation_id == command.correlation_id
                )
            ).all()
            == []
        )
        assert (
            connection.execute(
                select(CommandReceiptRow.idempotency_key).where(
                    CommandReceiptRow.idempotency_key == command.idempotency_key
                )
            ).scalar_one_or_none()
            is None
        )
        assert connection.execute(select(func.count(OutboxEventRow.id))).scalar_one() == 1


def test_processor_atomically_records_one_effect_receipt_audit_and_delivery(
    engine: Engine,
) -> None:
    seed_application_events(engine)
    result = OutboxProcessor(
        uow_factory=create_uow_factory(engine), environment="test"
    ).process_one()
    assert result.status == "delivered"
    with engine.connect() as connection:
        assert connection.execute(select(func.count(InternalEffectRow.id))).scalar_one() == 1
        assert connection.execute(select(func.count(ConsumerReceiptRow.event_id))).scalar_one() == 1
        assert (
            connection.execute(
                select(OutboxEventRow.status).where(OutboxEventRow.id == result.event_id)
            ).scalar_one()
            == OutboxStatus.DELIVERED.value
        )
        actions = connection.execute(
            select(AuditEventRow.action).where(AuditEventRow.entity_id == result.event_id)
        ).scalars()
        assert "execution.event_delivered" in set(actions)
        transitions = connection.execute(
            select(OutboxTransitionRow.transition)
            .where(OutboxTransitionRow.event_id == result.event_id)
            .order_by(OutboxTransitionRow.sequence)
        ).scalars()
        assert list(transitions) == [
            OutboxTransitionType.CLAIMED.value,
            OutboxTransitionType.DELIVERED.value,
        ]


def test_duplicate_consumer_delivery_is_suppressed_without_a_second_effect(
    engine: Engine,
) -> None:
    seed_application_events(engine)
    factory = create_uow_factory(engine)
    event_id = first_event_id(engine)
    now = datetime(2026, 8, 10, 12, 0, tzinfo=UTC)
    with factory() as uow:
        effect = InternalEffect(
            id="precommitted-effect",
            consumer_name="internal-redacted-projection-v1",
            event_id=event_id,
            owner_user_id=DEMO_USER_ID,
            effect_type="internal.redacted_event_projection.v1",
            occurred_at=now,
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
                processed_at=now,
            )
        )
        uow.commit()
    result = OutboxProcessor(uow_factory=factory, environment="test").process_one()
    assert result.event_id == event_id
    assert result.status == "delivered"
    with engine.connect() as connection:
        assert connection.execute(select(func.count(InternalEffectRow.id))).scalar_one() == 1
        assert (
            connection.execute(
                select(OutboxTransitionRow.transition)
                .where(OutboxTransitionRow.event_id == event_id)
                .order_by(OutboxTransitionRow.sequence.desc())
                .limit(1)
            ).scalar_one()
            == OutboxTransitionType.DUPLICATE_SUPPRESSED.value
        )


def test_retry_budget_failure_visibility_and_authorized_recovery(engine: Engine) -> None:
    seed_application_events(engine)
    factory = create_uow_factory(engine)
    handler: InternalEventHandler = AlwaysRetryHandler()
    processor = OutboxProcessor(
        uow_factory=factory,
        handlers={event_type: handler for event_type in InternalEventType},
        environment="test",
    )
    event_id = first_event_id(engine)
    for attempt in range(3):
        result = processor.process_one()
        assert result.event_id == event_id
        if attempt < 2:
            assert result.status == OutboxStatus.RETRY.value
            with engine.begin() as connection:
                connection.execute(
                    update(OutboxEventRow)
                    .where(OutboxEventRow.id == event_id)
                    .values(available_at=datetime(2026, 8, 10, tzinfo=UTC))
                )
        else:
            assert result.status == OutboxStatus.FAILED.value
    assert [
        event.id
        for event in processor.failed_for_owner(actor_id=DEMO_USER_ID, owner_user_id=DEMO_USER_ID)
    ] == [event_id]
    with pytest.raises(AuthorizationError):
        processor.failed_for_owner(actor_id=OTHER_USER_ID, owner_user_id=DEMO_USER_ID)
    with pytest.raises(AuthorizationError):
        processor.status_for_owner(actor_id=OTHER_USER_ID, owner_user_id=DEMO_USER_ID)
    with pytest.raises(AuthorizationError):
        processor.recover_failed(
            RecoverOutboxEventCommand(
                user_id=OTHER_USER_ID,
                event_id=event_id,
                reason="Cross-person recovery must fail.",
                correlation_id="execution-cross-person-recovery",
                idempotency_key="execution-cross-person-recovery-0001",
            )
        )
    command = RecoverOutboxEventCommand(
        user_id=DEMO_USER_ID,
        event_id=event_id,
        reason="Retry the synthetic internal projection after review.",
        correlation_id="execution-recovery-correlation",
        idempotency_key="execution-recovery-idempotency-0001",
    )
    recovered = processor.recover_failed(command)
    assert recovered.status is OutboxStatus.PENDING
    assert recovered.attempt_count == 0
    assert recovered.cycle == 1
    with engine.begin() as connection:
        connection.execute(
            update(OutboxEventRow)
            .where(OutboxEventRow.id == event_id)
            .values(
                status=OutboxStatus.DELIVERED.value,
                delivered_at=datetime.now(UTC),
            )
        )
    assert processor.recover_failed(command) == recovered
    with pytest.raises(ConflictError, match="idempotency key"):
        processor.recover_failed(
            RecoverOutboxEventCommand(
                user_id=DEMO_USER_ID,
                event_id=event_id,
                reason="Changed recovery reason must not reuse the key.",
                correlation_id="execution-recovery-mutation",
                idempotency_key=command.idempotency_key,
            )
        )
    with engine.connect() as connection:
        transitions = list(
            connection.execute(
                select(OutboxTransitionRow.transition)
                .where(OutboxTransitionRow.event_id == event_id)
                .order_by(OutboxTransitionRow.sequence)
            ).scalars()
        )
        receipt = connection.execute(
            select(
                CommandReceiptRow.command_type,
                CommandReceiptRow.outbox_event_id,
                CommandReceiptRow.result_json,
            ).where(CommandReceiptRow.idempotency_key == command.idempotency_key)
        ).one()
        current_status = connection.execute(
            select(OutboxEventRow.status).where(OutboxEventRow.id == event_id)
        ).scalar_one()
        recovery_audits = connection.execute(
            select(AuditEventRow.action, AuditEventRow.correlation_id).where(
                AuditEventRow.causation_id == command.idempotency_key,
                AuditEventRow.action == "execution.event_recovered",
            )
        ).all()
    assert transitions.count(OutboxTransitionType.RETRY_SCHEDULED.value) == 2
    assert transitions.count(OutboxTransitionType.RECOVERED.value) == 1
    assert transitions[-2:] == [
        OutboxTransitionType.FAILED.value,
        OutboxTransitionType.RECOVERED.value,
    ]
    assert receipt.command_type == "recover_outbox_event"
    assert receipt.outbox_event_id == event_id
    assert receipt.result_json is not None
    assert current_status == OutboxStatus.DELIVERED.value
    assert recovery_audits == [("execution.event_recovered", "execution-recovery-correlation")]


def test_exact_recovery_replay_reauthorizes_before_result_disclosure(
    engine: Engine,
) -> None:
    initialize_schema(engine)
    factory = create_uow_factory(engine)
    event_id = "recovery-reauthorization-event"
    occurred_at = datetime(2026, 8, 10, 7, 30, tzinfo=UTC)
    with factory() as uow:
        uow.outbox.enqueue(
            OutboxEvent(
                id=event_id,
                event_type=InternalEventType.INTENT_CAPTURED,
                schema_version=1,
                aggregate_type="intent",
                aggregate_id="recovery-reauthorization-intent",
                aggregate_version=1,
                owner_user_id=DEMO_USER_ID,
                controller_id=DEMO_USER_ID,
                data_subject_id=DEMO_USER_ID,
                actor_id=DEMO_USER_ID,
                on_behalf_of_id=None,
                sensitivity="personal",
                correlation_id="recovery-reauthorization-source",
                causation_id="recovery-reauthorization-causation",
                occurred_at=occurred_at,
                capability_mode="local-mock-synthetic",
                producer_key="recovery-reauthorization-producer",
                payload={"state": "captured"},
                status=OutboxStatus.FAILED,
                available_at=occurred_at,
                attempt_count=3,
                max_attempts=3,
                last_failure_code="synthetic-terminal",
            )
        )
        uow.commit()

    policy = RecoveryAllowedOncePolicy()
    processor = OutboxProcessor(
        uow_factory=factory,
        policy=policy,
        environment="test",
    )
    reason = "Retry once while recovery authority remains active."
    idempotency_key = "recovery-reauthorization-idempotency-0001"
    recovered = processor.recover_failed(
        RecoverOutboxEventCommand(
            user_id=DEMO_USER_ID,
            event_id=event_id,
            reason=reason,
            correlation_id="recovery-reauthorization-initial",
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
                correlation_id="recovery-reauthorization-replay-denied",
                idempotency_key=idempotency_key,
            )
        )

    assert policy.recovery_decisions == 2
    with engine.connect() as connection:
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
        "recovery-reauthorization-replay-denied",
        "denied:recovery-authority-revoked",
    )


def test_policy_is_rechecked_after_claim_and_immediately_before_effect(
    engine: Engine,
) -> None:
    seed_application_events(engine)
    policy = RevokedBeforeEffectPolicy()
    result = OutboxProcessor(
        uow_factory=create_uow_factory(engine),
        policy=policy,
        environment="test",
    ).process_one()
    assert policy.handle_decisions == 2
    assert result.status == OutboxStatus.FAILED.value
    assert result.failure_code == "authorization-revoked"
    with engine.connect() as connection:
        assert connection.execute(select(func.count(InternalEffectRow.id))).scalar_one() == 0
        assert (
            connection.execute(
                select(OutboxEventRow.last_failure_code).where(OutboxEventRow.id == result.event_id)
            ).scalar_one()
            == "authorization-revoked"
        )


def test_expired_claim_is_reclaimed_after_restart_with_a_new_fencing_token(
    engine: Engine,
) -> None:
    seed_application_events(engine)
    factory = create_uow_factory(engine)
    event_id = first_event_id(engine)
    with factory() as uow:
        first_claim = uow.outbox.claim_next("personal-os-worker:crashed", 30)
        assert first_claim is not None
        first_token = first_claim.lease_token
        uow.commit()
    with engine.begin() as connection:
        connection.execute(
            update(OutboxEventRow)
            .where(OutboxEventRow.id == event_id)
            .values(lease_expires_at=datetime(2026, 8, 10, tzinfo=UTC))
        )
    result = OutboxProcessor(
        uow_factory=factory,
        environment="test",
        instance_id="restart",
    ).process_one()
    assert result.event_id == event_id
    assert result.status == "delivered"
    with engine.connect() as connection:
        tokens = list(
            connection.execute(
                select(OutboxTransitionRow.lease_token)
                .where(
                    OutboxTransitionRow.event_id == event_id,
                    OutboxTransitionRow.transition.in_(
                        (
                            OutboxTransitionType.CLAIMED.value,
                            OutboxTransitionType.RECLAIMED.value,
                        )
                    ),
                )
                .order_by(OutboxTransitionRow.sequence)
            ).scalars()
        )
    assert len(tokens) == 2
    assert tokens[0] == first_token
    assert tokens[1] != first_token


def test_stale_lease_holder_cannot_commit_an_effect(engine: Engine) -> None:
    seed_application_events(engine)
    factory = create_uow_factory(engine)
    event_id = first_event_id(engine)
    with factory() as uow:
        claim = uow.outbox.claim_next("personal-os-worker:old", 30)
        assert claim is not None and claim.lease_token is not None
        old_token = claim.lease_token
        uow.commit()
    with engine.begin() as connection:
        connection.execute(
            update(OutboxEventRow)
            .where(OutboxEventRow.id == event_id)
            .values(
                lease_owner="personal-os-worker:new",
                lease_token="new-fencing-token",
                lease_expires_at=datetime.now(UTC) + timedelta(minutes=1),
            )
        )
    with factory() as uow:
        effect = InternalEffect(
            id="stale-effect",
            consumer_name="internal-redacted-projection-v1",
            event_id=event_id,
            owner_user_id=DEMO_USER_ID,
            effect_type="internal.redacted_event_projection.v1",
            occurred_at=datetime.now(UTC),
            payload={"event_type": "stale", "aggregate_type": "intent", "state": "bad"},
        )
        uow.internal_effects.add(effect)
        uow.consumer_receipts.add(
            ConsumerReceipt(
                consumer_name=effect.consumer_name,
                event_id=event_id,
                effect_id=effect.id,
                processed_at=datetime.now(UTC),
            )
        )
        with pytest.raises(ConflictError, match="stale"):
            uow.outbox.mark_delivered(
                event_id,
                "personal-os-worker:old",
                old_token,
            )
    with engine.connect() as connection:
        assert connection.execute(select(func.count(InternalEffectRow.id))).scalar_one() == 0
        assert connection.execute(select(func.count(ConsumerReceiptRow.event_id))).scalar_one() == 0


def test_unknown_handler_fails_closed_and_external_handler_registration_is_denied(
    engine: Engine,
) -> None:
    seed_application_events(engine)
    processor = OutboxProcessor(
        uow_factory=create_uow_factory(engine),
        handlers={},
        environment="test",
    )
    result = processor.process_one()
    assert result.status == OutboxStatus.FAILED.value
    assert result.failure_code == "unknown-handler"

    class ExternalHandler(AlwaysRetryHandler):
        mode = "external-live"
        action_level = 4

    with pytest.raises(ProhibitedCapabilityError, match="external or high-authority"):
        OutboxProcessor(
            uow_factory=create_uow_factory(engine),
            handlers={InternalEventType.INTENT_CAPTURED: ExternalHandler()},
            environment="test",
        )


def test_failed_work_api_is_owner_scoped_and_recovery_is_explicit(
    client: TestClient, engine: Engine
) -> None:
    factory = create_uow_factory(engine)
    occurred_at = datetime(2026, 8, 10, 7, 0, tzinfo=UTC)
    with factory() as uow:
        for event_id, owner_id in (
            ("failed-own-event", DEMO_USER_ID),
            ("failed-other-event", OTHER_USER_ID),
        ):
            uow.outbox.enqueue(
                OutboxEvent(
                    id=event_id,
                    event_type=InternalEventType.INTENT_CAPTURED,
                    schema_version=1,
                    aggregate_type="intent",
                    aggregate_id=f"aggregate-{event_id}",
                    aggregate_version=1,
                    owner_user_id=owner_id,
                    controller_id=owner_id,
                    data_subject_id=owner_id,
                    actor_id=owner_id,
                    on_behalf_of_id=None,
                    sensitivity="personal",
                    correlation_id=f"correlation-{event_id}",
                    causation_id=f"causation-{event_id}",
                    occurred_at=occurred_at,
                    capability_mode="local-mock-synthetic",
                    producer_key=f"producer-{event_id}",
                    payload={"state": "captured"},
                    status=OutboxStatus.FAILED,
                    available_at=occurred_at,
                    attempt_count=3,
                    max_attempts=3,
                    last_failure_code="synthetic-terminal",
                )
            )
        uow.commit()
    failed = client.get("/v1/execution/failed")
    assert failed.status_code == 200
    assert [event["id"] for event in failed.json()] == ["failed-own-event"]
    denied = client.post(
        "/v1/execution/failed-other-event/recover",
        json={"reason": "Cross-person recovery must not disclose or mutate."},
        headers={"Idempotency-Key": "api-cross-person-recovery-0001"},
    )
    assert denied.status_code == 404
    recovered = client.post(
        "/v1/execution/failed-own-event/recover",
        json={"reason": "Retry after explicit local operator review."},
        headers={
            "Idempotency-Key": "api-own-recovery-0001",
            "X-Correlation-ID": "api-own-recovery-correlation",
        },
    )
    assert recovered.status_code == 200
    assert recovered.json()["status"] == OutboxStatus.PENDING.value
    assert recovered.json()["cycle"] == 1
    replayed = client.post(
        "/v1/execution/failed-own-event/recover",
        json={"reason": "Retry after explicit local operator review."},
        headers={
            "Idempotency-Key": "api-own-recovery-0001",
            "X-Correlation-ID": "api-own-recovery-replay-correlation",
        },
    )
    assert replayed.status_code == 200
    assert replayed.json() == recovered.json()
    mutated = client.post(
        "/v1/execution/failed-own-event/recover",
        json={"reason": "A changed reason cannot reuse the same key."},
        headers={
            "Idempotency-Key": "api-own-recovery-0001",
            "X-Correlation-ID": "api-own-recovery-mutation",
        },
    )
    assert mutated.status_code == 409
    with engine.connect() as connection:
        assert (
            connection.execute(
                select(func.count(OutboxTransitionRow.id)).where(
                    OutboxTransitionRow.event_id == "failed-own-event",
                    OutboxTransitionRow.transition == OutboxTransitionType.RECOVERED.value,
                )
            ).scalar_one()
            == 1
        )
        assert (
            connection.execute(
                select(func.count(AuditEventRow.id)).where(
                    AuditEventRow.action == "command.idempotency_reuse_denied",
                    AuditEventRow.correlation_id == "api-own-recovery-mutation",
                )
            ).scalar_one()
            == 1
        )
