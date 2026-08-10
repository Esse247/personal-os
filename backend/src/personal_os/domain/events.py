from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum

from personal_os.domain.errors import ValidationError
from personal_os.domain.provenance import require_aware


class InternalEventType(StrEnum):
    INTENT_CAPTURED = "intent.captured.v1"
    INTENT_CLARIFICATION_REQUESTED = "intent.clarification_requested.v1"
    COMMITMENT_CREATED = "commitment.created.v1"
    SCHEDULE_NO_FEASIBLE_PROPOSAL = "schedule.no_feasible_proposal.v1"
    SCHEDULE_PROPOSED = "schedule.proposed.v1"
    SCHEDULE_APPROVED = "schedule.approved.v1"
    SCHEDULE_REJECTED = "schedule.rejected.v1"
    SCHEDULE_CHANGED = "schedule.changed.v1"
    COMMAND_DENIED = "command.denied.v1"


class OutboxStatus(StrEnum):
    PENDING = "pending"
    PROCESSING = "processing"
    RETRY = "retry"
    DELIVERED = "delivered"
    FAILED = "failed"


class OutboxTransitionType(StrEnum):
    CLAIMED = "claimed"
    RECLAIMED = "reclaimed"
    RETRY_SCHEDULED = "retry_scheduled"
    DELIVERED = "delivered"
    FAILED = "failed"
    RECOVERED = "recovered"
    DUPLICATE_SUPPRESSED = "duplicate_suppressed"


EventPayloadValue = str | int | bool | None
ALLOWED_PAYLOAD_KEYS = frozenset({"state", "result", "reason_code"})
ALLOWED_SENSITIVITIES = frozenset(
    {"public", "household_shared", "personal", "financial", "health", "identity", "legal"}
)
FAILURE_CODE_PATTERN = re.compile(r"^[a-z0-9][a-z0-9-]{0,63}$")


@dataclass(frozen=True, slots=True)
class OutboxEvent:
    id: str
    event_type: InternalEventType
    schema_version: int
    aggregate_type: str
    aggregate_id: str
    aggregate_version: int
    owner_user_id: str
    controller_id: str
    data_subject_id: str
    actor_id: str
    on_behalf_of_id: str | None
    sensitivity: str
    correlation_id: str
    causation_id: str
    occurred_at: datetime
    capability_mode: str
    producer_key: str
    payload: dict[str, EventPayloadValue]
    status: OutboxStatus = OutboxStatus.PENDING
    available_at: datetime | None = None
    attempt_count: int = 0
    max_attempts: int = 3
    cycle: int = 0
    lease_owner: str | None = None
    lease_token: str | None = None
    lease_expires_at: datetime | None = None
    last_failure_code: str | None = None
    delivered_at: datetime | None = None

    def __post_init__(self) -> None:
        require_aware(self.occurred_at, "occurred_at")
        if self.available_at is not None:
            require_aware(self.available_at, "available_at")
        if self.lease_expires_at is not None:
            require_aware(self.lease_expires_at, "lease_expires_at")
        if self.delivered_at is not None:
            require_aware(self.delivered_at, "delivered_at")
        required = (
            self.id,
            self.aggregate_type,
            self.aggregate_id,
            self.owner_user_id,
            self.controller_id,
            self.data_subject_id,
            self.actor_id,
            self.sensitivity,
            self.correlation_id,
            self.causation_id,
            self.capability_mode,
            self.producer_key,
        )
        if any(not value.strip() for value in required):
            raise ValidationError("canonical event envelope fields cannot be empty")
        if self.schema_version != 1:
            raise ValidationError("only canonical event schema version 1 is supported")
        if self.sensitivity not in ALLOWED_SENSITIVITIES:
            raise ValidationError("canonical event sensitivity is not recognized")
        if self.capability_mode != "local-mock-synthetic":
            raise ValidationError("canonical events must remain local, mock, and synthetic")
        if self.aggregate_version < 0:
            raise ValidationError("event aggregate version cannot be negative")
        if not 1 <= self.max_attempts <= 10:
            raise ValidationError("outbox max attempts must be between 1 and 10")
        if not 0 <= self.attempt_count <= self.max_attempts:
            raise ValidationError("outbox attempt count is outside its bounded budget")
        if self.cycle < 0:
            raise ValidationError("outbox recovery cycle cannot be negative")
        if set(self.payload) - ALLOWED_PAYLOAD_KEYS:
            raise ValidationError("canonical event payload contains a non-allowlisted key")
        for value in self.payload.values():
            if isinstance(value, str) and len(value) > 160:
                raise ValidationError("canonical event payload strings are limited to 160 chars")
            if not isinstance(value, (str, int, bool, type(None))):
                raise ValidationError("canonical event payload values must be scalar")
        encoded = json.dumps(self.payload, sort_keys=True, separators=(",", ":"))
        if len(encoded.encode("utf-8")) > 2048:
            raise ValidationError("canonical event payload exceeds the redacted size limit")
        has_lease = all(
            value is not None
            for value in (self.lease_owner, self.lease_token, self.lease_expires_at)
        )
        if self.status is OutboxStatus.PROCESSING and not has_lease:
            raise ValidationError("processing outbox events require a complete lease")
        if self.status is not OutboxStatus.PROCESSING and any(
            value is not None
            for value in (self.lease_owner, self.lease_token, self.lease_expires_at)
        ):
            raise ValidationError("non-processing outbox events cannot retain a lease")
        if self.last_failure_code is not None and not FAILURE_CODE_PATTERN.fullmatch(
            self.last_failure_code
        ):
            raise ValidationError("outbox failure code is not a typed redacted code")
        if self.status in {OutboxStatus.RETRY, OutboxStatus.FAILED}:
            if self.last_failure_code is None:
                raise ValidationError("retry and failed events require a failure code")
        elif self.last_failure_code is not None:
            raise ValidationError("only retry or failed events can retain a failure code")
        if (self.status is OutboxStatus.DELIVERED) != (self.delivered_at is not None):
            raise ValidationError("delivered timestamp must match delivered state")


@dataclass(frozen=True, slots=True)
class ConsumerReceipt:
    consumer_name: str
    event_id: str
    effect_id: str
    processed_at: datetime

    def __post_init__(self) -> None:
        require_aware(self.processed_at, "processed_at")
        if (
            not self.consumer_name.strip()
            or not self.event_id.strip()
            or not self.effect_id.strip()
        ):
            raise ValidationError("consumer receipt identifiers cannot be empty")


@dataclass(frozen=True, slots=True)
class InternalEffect:
    id: str
    consumer_name: str
    event_id: str
    owner_user_id: str
    effect_type: str
    occurred_at: datetime
    payload: dict[str, EventPayloadValue] = field(default_factory=dict)

    def __post_init__(self) -> None:
        require_aware(self.occurred_at, "occurred_at")
        if self.effect_type != "internal.redacted_event_projection.v1":
            raise ValidationError("only the internal redacted projection effect is registered")
        if any(
            not value.strip()
            for value in (self.id, self.consumer_name, self.event_id, self.owner_user_id)
        ):
            raise ValidationError("internal effect identifiers cannot be empty")
        if set(self.payload) - {"event_type", "aggregate_type", "state"}:
            raise ValidationError("internal effect payload contains a non-allowlisted key")
        for value in self.payload.values():
            if isinstance(value, str) and len(value) > 160:
                raise ValidationError("internal effect strings are limited to 160 chars")
            if not isinstance(value, (str, int, bool, type(None))):
                raise ValidationError("internal effect payload values must be scalar")
        encoded = json.dumps(self.payload, sort_keys=True, separators=(",", ":"))
        if len(encoded.encode("utf-8")) > 2048:
            raise ValidationError("internal effect payload exceeds the redacted size limit")


@dataclass(frozen=True, slots=True)
class OutboxTransition:
    id: str
    event_id: str
    sequence: int
    cycle: int
    attempt_number: int
    transition: OutboxTransitionType
    occurred_at: datetime
    worker_id: str | None = None
    lease_token: str | None = None
    actor_id: str | None = None
    failure_code: str | None = None
    policy_result: str | None = None
    reason: str | None = None

    def __post_init__(self) -> None:
        require_aware(self.occurred_at, "occurred_at")
        if self.sequence < 1 or self.cycle < 0 or self.attempt_number < 0:
            raise ValidationError("outbox transition ordinals cannot be negative")
        if self.failure_code is not None and not FAILURE_CODE_PATTERN.fullmatch(self.failure_code):
            raise ValidationError("outbox transition failure code is invalid")
        if self.reason is not None and not 1 <= len(self.reason.strip()) <= 240:
            raise ValidationError("outbox recovery reason must be 1-240 characters")
