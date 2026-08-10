from __future__ import annotations

import json
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
from hashlib import sha256
from typing import Protocol
from uuid import uuid4

from personal_os.application.commands import (
    ExecutionEventResult,
    RecoverOutboxEventCommand,
)
from personal_os.application.policy import (
    AuthContext,
    FoundationPolicy,
    PolicyDecision,
    ResourceRef,
)
from personal_os.domain.entities import AuditEvent, CommandReceipt
from personal_os.domain.errors import (
    AuthorizationError,
    ConflictError,
    LockTimeoutError,
    ProhibitedCapabilityError,
    ValidationError,
)
from personal_os.domain.events import (
    ConsumerReceipt,
    InternalEffect,
    InternalEventType,
    OutboxEvent,
    OutboxStatus,
)
from personal_os.domain.provenance import SourceType
from personal_os.ports.repositories import UnitOfWork

UnitOfWorkFactory = Callable[[], UnitOfWork]
Clock = Callable[[], datetime]
IdFactory = Callable[[], str]


def worker_clock() -> datetime:
    return datetime.now(UTC)


def worker_id() -> str:
    return str(uuid4())


@dataclass(frozen=True, slots=True)
class JobEnvelope:
    id: str
    action: str
    actor_id: str
    owner_user_id: str
    permission: str
    purpose: str
    environment: str
    action_level: int
    correlation_id: str
    idempotency_key: str
    max_attempts: int


class FoundationWorker:
    """Boundary placeholder: v0.1 performs no external or autonomous work."""

    ALLOWED_ACTION = "foundation.simulate.noop"

    def __init__(self, policy: FoundationPolicy | None = None) -> None:
        self.policy = policy or FoundationPolicy()

    def run(self, job: JobEnvelope) -> dict[str, str]:
        if (
            job.action != self.ALLOWED_ACTION
            or job.environment not in {"development", "test"}
            or job.action_level > 2
        ):
            raise ProhibitedCapabilityError("worker action is not registered in Foundation v0.1")
        rule_id = self.policy.authorize(
            AuthContext(job.actor_id, job.purpose),
            job.permission,
            ResourceRef("worker_job", job.id, job.owner_user_id, "personal"),
        )
        return {
            "job_id": job.id,
            "status": "simulated",
            "mode": "mock-only",
            "action": job.action,
            "policy_rule": rule_id,
        }


class InternalEventHandler(Protocol):
    @property
    def consumer_name(self) -> str: ...

    @property
    def mode(self) -> str: ...

    @property
    def action_level(self) -> int: ...

    def build_effect(
        self, event: OutboxEvent, *, effect_id: str, occurred_at: datetime
    ) -> InternalEffect: ...


@dataclass(frozen=True, slots=True)
class InternalProjectionHandler:
    consumer_name: str = "internal-redacted-projection-v1"
    mode: str = "internal-mock-only"
    action_level: int = 3

    def build_effect(
        self, event: OutboxEvent, *, effect_id: str, occurred_at: datetime
    ) -> InternalEffect:
        state = event.payload.get("state")
        return InternalEffect(
            id=effect_id,
            consumer_name=self.consumer_name,
            event_id=event.id,
            owner_user_id=event.owner_user_id,
            effect_type="internal.redacted_event_projection.v1",
            occurred_at=occurred_at,
            payload={
                "event_type": event.event_type.value,
                "aggregate_type": event.aggregate_type,
                "state": state if isinstance(state, str) else None,
            },
        )


@dataclass(frozen=True, slots=True)
class ProcessingResult:
    event_id: str | None
    status: str
    failure_code: str | None = None


class RetryableExecutionError(RuntimeError):
    def __init__(self, failure_code: str) -> None:
        from personal_os.domain.events import FAILURE_CODE_PATTERN

        if not FAILURE_CODE_PATTERN.fullmatch(failure_code):
            raise ValueError("retryable execution errors require a typed failure code")
        super().__init__("internal handler requested a typed retry")
        self.failure_code = failure_code


class InvalidHandlerEnvelopeError(RuntimeError):
    """A registered handler returned an effect outside its claimed event envelope."""


class OutboxProcessor:
    """Fenced, policy-gated processor for the one local v0.2 internal effect."""

    WORKER_ACTOR = FoundationPolicy.EXECUTION_WORKER_ID
    RECOVERY_COMMAND_TYPE = "recover_outbox_event"

    def __init__(
        self,
        *,
        uow_factory: UnitOfWorkFactory,
        policy: FoundationPolicy | None = None,
        handlers: Mapping[InternalEventType, InternalEventHandler] | None = None,
        environment: str = "development",
        instance_id: str = "local-1",
        lease_seconds: int = 30,
        clock: Clock = worker_clock,
        id_factory: IdFactory = worker_id,
    ) -> None:
        self.uow_factory = uow_factory
        self.policy = policy or FoundationPolicy()
        self.environment = environment
        self.lease_seconds = lease_seconds
        self.clock = clock
        self.id_factory = id_factory
        if environment not in {"development", "test"}:
            raise ProhibitedCapabilityError("outbox execution is local development/test only")
        if not instance_id.strip() or len(instance_id) > 32:
            raise ValueError("worker instance identity must be 1-32 characters")
        self.lease_owner = f"{self.WORKER_ACTOR}:{instance_id}"
        default_handler = InternalProjectionHandler()
        selected_handlers: Mapping[InternalEventType, InternalEventHandler] = (
            handlers
            if handlers is not None
            else {event_type: default_handler for event_type in InternalEventType}
        )
        self.handlers: dict[InternalEventType, InternalEventHandler] = dict(selected_handlers)
        for event_type, handler in self.handlers.items():
            if not isinstance(event_type, InternalEventType):
                raise ProhibitedCapabilityError("worker handler key is not a canonical event")
            if handler.mode != "internal-mock-only" or handler.action_level > 3:
                raise ProhibitedCapabilityError("external or high-authority worker handler denied")

    def process_one(self) -> ProcessingResult:
        with self.uow_factory() as uow:
            event = uow.outbox.claim_next(self.lease_owner, self.lease_seconds)
            if event is None:
                return ProcessingResult(None, "idle")
            if event.status is OutboxStatus.FAILED:
                self._append_audit(
                    uow,
                    event,
                    action="execution.event_failed",
                    outcome="failed",
                    policy_result="denied:attempt-budget-exhausted",
                    failure_code=event.last_failure_code,
                )
                uow.commit()
                return ProcessingResult(event.id, "failed", event.last_failure_code)
            decision = self._handle_decision(event)
            if not decision.allowed:
                failed = uow.outbox.record_failure(
                    event.id,
                    self.lease_owner,
                    self._lease_token(event),
                    "authorization-denied",
                    retryable=False,
                    policy_result=f"denied:{decision.rule_id}",
                )
                self._append_audit(
                    uow,
                    failed,
                    action="execution.authorization_denied",
                    outcome="denied",
                    policy_result=f"denied:{decision.rule_id}",
                    failure_code="authorization-denied",
                )
                uow.commit()
                return ProcessingResult(event.id, "failed", "authorization-denied")
            uow.commit()

        handler = self.handlers.get(event.event_type)
        if handler is None:
            return self._record_failure(
                event,
                "unknown-handler",
                retryable=False,
                policy_result="denied:unknown-handler",
            )
        try:
            return self._deliver(event, handler)
        except RetryableExecutionError as exc:
            return self._record_failure(
                event,
                exc.failure_code,
                retryable=True,
                policy_result="denied:retryable-handler-failure",
            )
        except AuthorizationError:
            return self._record_failure(
                event,
                "authorization-revoked",
                retryable=False,
                policy_result="denied:authorization-revoked",
            )
        except InvalidHandlerEnvelopeError:
            return self._record_failure(
                event,
                "handler-envelope-invalid",
                retryable=False,
                policy_result="denied:handler-envelope-invalid",
            )
        except ConflictError:
            return ProcessingResult(event.id, "stale", "stale-lease")
        except Exception:
            return self._record_failure(
                event,
                "handler-error",
                retryable=True,
                policy_result="denied:typed-handler-error",
            )

    def recover_failed(self, command: RecoverOutboxEventCommand) -> ExecutionEventResult:
        request_digest = self._recovery_request_digest(command)
        with self.uow_factory() as uow:
            event = uow.outbox.get(command.event_id)
            if event is None:
                raise AuthorizationError("resource not found")

            context = AuthContext(
                command.user_id,
                "recover failed internal event",
                environment=self.environment,
            )
            # PostgreSQL exact retries serialize on this transaction-scoped key lock. The
            # repository bounds that wait and preserves this outer transaction through a
            # savepoint so an authorized timeout remains visible and auditable. The policy
            # decision stays after the wait and immediately before any receipt disclosure.
            try:
                uow.receipts.lock_key(command.idempotency_key)
            except LockTimeoutError as exc:
                timeout_decision = self.policy.decide(
                    context,
                    FoundationPolicy.RECOVER_PERMISSION,
                    self._resource(event),
                )
                if not timeout_decision.allowed:
                    self._append_audit(
                        uow,
                        event,
                        action="execution.recovery_denied",
                        outcome="denied",
                        policy_result=f"denied:{timeout_decision.rule_id}",
                        actor_id=command.user_id,
                        failure_code="recovery-authorization-denied",
                        correlation_id=command.correlation_id,
                        causation_id=command.idempotency_key,
                    )
                    uow.commit()
                    raise AuthorizationError("resource not found") from exc
                self._append_audit(
                    uow,
                    event,
                    action="execution.recovery_deferred",
                    outcome="failed",
                    policy_result=f"allowed:{timeout_decision.rule_id}",
                    actor_id=command.user_id,
                    failure_code="recovery-lock-timeout",
                    correlation_id=command.correlation_id,
                    causation_id=command.idempotency_key,
                )
                uow.commit()
                raise
            decision = self.policy.decide(
                context,
                FoundationPolicy.RECOVER_PERMISSION,
                self._resource(event),
            )
            if not decision.allowed:
                self._append_audit(
                    uow,
                    event,
                    action="execution.recovery_denied",
                    outcome="denied",
                    policy_result=f"denied:{decision.rule_id}",
                    actor_id=command.user_id,
                    failure_code="recovery-authorization-denied",
                    correlation_id=command.correlation_id,
                    causation_id=command.idempotency_key,
                )
                uow.commit()
                raise AuthorizationError("resource not found")

            receipt = uow.receipts.get(command.idempotency_key)
            if receipt is not None:
                if (
                    receipt.user_id != command.user_id
                    or receipt.command_type != self.RECOVERY_COMMAND_TYPE
                    or receipt.request_digest != request_digest
                    or receipt.outbox_event_id != command.event_id
                    or receipt.result_json is None
                ):
                    self._append_recovery_receipt_denial(uow, command)
                    uow.commit()
                    raise ConflictError("idempotency key was already used for a different command")
                return self._replay_recovery(receipt)

            recovered = uow.outbox.recover(
                event.id,
                command.user_id,
                command.reason,
                f"allowed:{decision.rule_id}",
            )
            result = self._event_result(recovered)
            uow.receipts.add(
                CommandReceipt(
                    idempotency_key=command.idempotency_key,
                    user_id=command.user_id,
                    command_type=self.RECOVERY_COMMAND_TYPE,
                    request_digest=request_digest,
                    created_at=self.clock(),
                    outbox_event_id=recovered.id,
                    result_json=self._serialize_event_result(result),
                )
            )
            self._append_audit(
                uow,
                recovered,
                action="execution.event_recovered",
                outcome="succeeded",
                policy_result=f"allowed:{decision.rule_id}",
                actor_id=command.user_id,
                correlation_id=command.correlation_id,
                causation_id=command.idempotency_key,
            )
            uow.commit()
            return result

    def failed_for_owner(self, *, actor_id: str, owner_user_id: str) -> list[OutboxEvent]:
        self._authorize_execution_read(actor_id, owner_user_id)
        with self.uow_factory() as uow:
            return uow.outbox.list_failed(owner_user_id)

    def status_for_owner(self, *, actor_id: str, owner_user_id: str) -> dict[OutboxStatus, int]:
        self._authorize_execution_read(actor_id, owner_user_id)
        with self.uow_factory() as uow:
            return uow.outbox.status_counts(owner_user_id)

    def _deliver(self, claimed: OutboxEvent, handler: InternalEventHandler) -> ProcessingResult:
        with self.uow_factory() as uow:
            event = uow.outbox.get(claimed.id)
            if event is None:
                raise ConflictError("outbox event is unavailable")
            decision = self._handle_decision(event)
            if not decision.allowed:
                raise AuthorizationError("resource not found")
            consumer_name = handler.consumer_name
            event_id = event.id
            owner_user_id = event.owner_user_id
            state = event.payload.get("state")
            expected_payload = {
                "event_type": event.event_type.value,
                "aggregate_type": event.aggregate_type,
                "state": state if isinstance(state, str) else None,
            }
            existing = uow.consumer_receipts.get(consumer_name, event_id)
            duplicate = existing is not None
            if existing is None:
                occurred_at = self.clock()
                effect_id = self.id_factory()
                try:
                    effect = handler.build_effect(
                        event,
                        effect_id=effect_id,
                        occurred_at=occurred_at,
                    )
                except ValidationError as exc:
                    raise InvalidHandlerEnvelopeError from exc
                self._validate_effect_binding(
                    effect,
                    effect_id=effect_id,
                    consumer_name=consumer_name,
                    event_id=event_id,
                    owner_user_id=owner_user_id,
                    occurred_at=occurred_at,
                    expected_payload=expected_payload,
                )
                uow.internal_effects.add(effect)
                uow.consumer_receipts.add(
                    ConsumerReceipt(
                        consumer_name=consumer_name,
                        event_id=event_id,
                        effect_id=effect.id,
                        processed_at=occurred_at,
                    )
                )
            delivered = uow.outbox.mark_delivered(
                event_id,
                self.lease_owner,
                self._lease_token(claimed),
                duplicate_suppressed=duplicate,
            )
            self._append_audit(
                uow,
                delivered,
                action=(
                    "execution.duplicate_suppressed" if duplicate else "execution.event_delivered"
                ),
                outcome="succeeded",
                policy_result=f"allowed:{decision.rule_id}",
                consumer_name=consumer_name,
            )
            uow.commit()
            return ProcessingResult(event_id, "delivered")

    @staticmethod
    def _validate_effect_binding(
        effect: InternalEffect,
        *,
        effect_id: str,
        consumer_name: str,
        event_id: str,
        owner_user_id: str,
        occurred_at: datetime,
        expected_payload: Mapping[str, str | int | bool | None],
    ) -> None:
        if not isinstance(effect, InternalEffect) or (
            effect.id != effect_id
            or effect.consumer_name != consumer_name
            or effect.event_id != event_id
            or effect.owner_user_id != owner_user_id
            or effect.effect_type != "internal.redacted_event_projection.v1"
            or effect.occurred_at != occurred_at
            or effect.payload != expected_payload
        ):
            raise InvalidHandlerEnvelopeError

    def _record_failure(
        self,
        claimed: OutboxEvent,
        failure_code: str,
        *,
        retryable: bool,
        policy_result: str,
    ) -> ProcessingResult:
        try:
            with self.uow_factory() as uow:
                failed = uow.outbox.record_failure(
                    claimed.id,
                    self.lease_owner,
                    self._lease_token(claimed),
                    failure_code,
                    retryable=retryable,
                    policy_result=policy_result,
                )
                self._append_audit(
                    uow,
                    failed,
                    action=(
                        "execution.retry_scheduled"
                        if failed.status is OutboxStatus.RETRY
                        else "execution.event_failed"
                    ),
                    outcome="failed",
                    policy_result=policy_result,
                    failure_code=failure_code,
                )
                uow.commit()
                return ProcessingResult(claimed.id, failed.status.value, failure_code)
        except ConflictError:
            return ProcessingResult(claimed.id, "stale", "stale-lease")

    def _handle_decision(self, event: OutboxEvent) -> PolicyDecision:
        return self.policy.decide(
            AuthContext(
                self.WORKER_ACTOR,
                "deliver committed internal event",
                delegation_id=event.owner_user_id,
                environment=self.environment,
            ),
            FoundationPolicy.HANDLE_PERMISSION,
            self._resource(event),
        )

    def _authorize_execution_read(self, actor_id: str, owner_user_id: str) -> None:
        self.policy.authorize(
            AuthContext(
                actor_id,
                "read local execution state",
                environment=self.environment,
            ),
            FoundationPolicy.READ_EXECUTION_PERMISSION,
            ResourceRef(
                "outbox_event",
                "owner-scoped-collection",
                owner_user_id,
                "personal",
            ),
        )

    @staticmethod
    def _recovery_request_digest(command: RecoverOutboxEventCommand) -> str:
        payload = {
            "command_type": OutboxProcessor.RECOVERY_COMMAND_TYPE,
            "event_id": command.event_id,
            "reason": command.reason.strip(),
            "user_id": command.user_id,
        }
        return sha256(
            json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
        ).hexdigest()

    @staticmethod
    def _event_result(event: OutboxEvent) -> ExecutionEventResult:
        return ExecutionEventResult(
            id=event.id,
            event_type=event.event_type,
            status=event.status,
            attempt_count=event.attempt_count,
            max_attempts=event.max_attempts,
            cycle=event.cycle,
            last_failure_code=event.last_failure_code,
            occurred_at=event.occurred_at,
        )

    @staticmethod
    def _serialize_event_result(result: ExecutionEventResult) -> str:
        return json.dumps(
            {
                "attempt_count": result.attempt_count,
                "cycle": result.cycle,
                "event_type": result.event_type.value,
                "id": result.id,
                "last_failure_code": result.last_failure_code,
                "max_attempts": result.max_attempts,
                "occurred_at": result.occurred_at.isoformat(),
                "status": result.status.value,
            },
            sort_keys=True,
            separators=(",", ":"),
        )

    @staticmethod
    def _replay_recovery(receipt: CommandReceipt) -> ExecutionEventResult:
        try:
            payload = json.loads(receipt.result_json or "")
            if not isinstance(payload, dict):
                raise TypeError
            expected_types = {
                "attempt_count": int,
                "cycle": int,
                "event_type": str,
                "id": str,
                "max_attempts": int,
                "occurred_at": str,
                "status": str,
            }
            if any(type(payload.get(key)) is not value for key, value in expected_types.items()):
                raise TypeError
            last_failure_code = payload.get("last_failure_code")
            if last_failure_code is not None and not isinstance(last_failure_code, str):
                raise TypeError
            if payload["id"] != receipt.outbox_event_id:
                raise ValueError
            return ExecutionEventResult(
                id=payload["id"],
                event_type=InternalEventType(payload["event_type"]),
                status=OutboxStatus(payload["status"]),
                attempt_count=payload["attempt_count"],
                max_attempts=payload["max_attempts"],
                cycle=payload["cycle"],
                last_failure_code=last_failure_code,
                occurred_at=datetime.fromisoformat(payload["occurred_at"]),
            )
        except (KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
            raise ConflictError("recovery receipt contains an invalid result snapshot") from exc

    def _append_recovery_receipt_denial(
        self, uow: UnitOfWork, command: RecoverOutboxEventCommand
    ) -> None:
        uow.audit.append(
            AuditEvent(
                id=self.id_factory(),
                user_id=command.user_id,
                action="command.idempotency_reuse_denied",
                entity_type="command_receipt",
                entity_id="protected-idempotency-key",
                correlation_id=command.correlation_id,
                occurred_at=self.clock(),
                outcome="denied",
                source_type=SourceType.USER_STATED.value,
                source_identifier=f"command:{command.idempotency_key}",
                actor_id=command.user_id,
                on_behalf_of_id=None,
                entity_version=0,
                causation_id=command.idempotency_key,
                policy_result="denied:idempotency-key-reuse",
                capability_mode="local-mock-synthetic",
                summary=("Idempotency-key reuse with changed recovery content was denied."),
                details={},
            )
        )

    @staticmethod
    def _resource(event: OutboxEvent) -> ResourceRef:
        return ResourceRef(
            "outbox_event",
            event.id,
            event.owner_user_id,
            event.sensitivity,
        )

    @staticmethod
    def _lease_token(event: OutboxEvent) -> str:
        if event.lease_token is None:
            raise ConflictError("outbox event has no active fencing token")
        return event.lease_token

    def _append_audit(
        self,
        uow: UnitOfWork,
        event: OutboxEvent,
        *,
        action: str,
        outcome: str,
        policy_result: str,
        actor_id: str | None = None,
        failure_code: str | None = None,
        consumer_name: str | None = None,
        correlation_id: str | None = None,
        causation_id: str | None = None,
    ) -> None:
        current_actor = actor_id or self.WORKER_ACTOR
        details: dict[str, str | int | float | bool | None] = {
            "event_type": event.event_type.value,
            "failure_code": failure_code,
            "consumer": consumer_name,
            "attempt_count": event.attempt_count,
            "cycle": event.cycle,
        }
        uow.audit.append(
            AuditEvent(
                id=self.id_factory(),
                user_id=event.owner_user_id,
                action=action,
                entity_type="outbox_event",
                entity_id=event.id,
                correlation_id=correlation_id or event.correlation_id,
                occurred_at=self.clock(),
                outcome=outcome,
                source_type=SourceType.SYSTEM_INFERRED.value,
                source_identifier=f"outbox:{event.id}",
                actor_id=current_actor,
                on_behalf_of_id=(
                    None if current_actor == event.owner_user_id else event.owner_user_id
                ),
                entity_version=event.cycle,
                causation_id=causation_id or event.causation_id,
                policy_result=policy_result,
                capability_mode=event.capability_mode,
                agent_reference=self.WORKER_ACTOR,
                summary="A local internal outbox transition was recorded.",
                details=details,
            )
        )
