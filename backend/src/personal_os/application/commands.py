from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum

from personal_os.domain.entities import Commitment, Intent, ScheduleProposal
from personal_os.domain.errors import ValidationError
from personal_os.domain.events import InternalEventType, OutboxStatus
from personal_os.domain.provenance import require_aware


class ProposalDecision(StrEnum):
    APPROVE = "approve"
    CHANGE = "change"
    REJECT = "reject"


@dataclass(frozen=True, slots=True)
class CaptureIntentCommand:
    user_id: str
    raw_text: str
    correlation_id: str
    idempotency_key: str


@dataclass(frozen=True, slots=True)
class CaptureIntentResult:
    intent: Intent
    commitment: Commitment | None
    proposal: ScheduleProposal | None


@dataclass(frozen=True, slots=True)
class DecideProposalCommand:
    user_id: str
    proposal_id: str
    decision: ProposalDecision
    expected_version: int
    correlation_id: str
    idempotency_key: str
    requested_start: datetime | None = None


@dataclass(frozen=True, slots=True)
class DecideProposalResult:
    proposal: ScheduleProposal
    replacement: ScheduleProposal | None
    commitment: Commitment


@dataclass(frozen=True, slots=True)
class RecoverOutboxEventCommand:
    user_id: str
    event_id: str
    reason: str
    correlation_id: str
    idempotency_key: str

    def __post_init__(self) -> None:
        if any(
            not value.strip()
            for value in (
                self.user_id,
                self.event_id,
                self.reason,
                self.correlation_id,
                self.idempotency_key,
            )
        ):
            raise ValidationError("execution recovery command fields cannot be empty")
        if not 1 <= len(self.reason.strip()) <= 240:
            raise ValidationError("execution recovery reason must be 1-240 characters")
        if len(self.correlation_id) > 64:
            raise ValidationError("execution recovery correlation ID is too long")
        if not 8 <= len(self.idempotency_key) <= 128:
            raise ValidationError("execution recovery idempotency key must be 8-128 characters")


@dataclass(frozen=True, slots=True)
class ExecutionEventResult:
    id: str
    event_type: InternalEventType
    status: OutboxStatus
    attempt_count: int
    max_attempts: int
    cycle: int
    last_failure_code: str | None
    occurred_at: datetime

    def __post_init__(self) -> None:
        require_aware(self.occurred_at, "occurred_at")
        if not self.id.strip():
            raise ValidationError("execution event result ID cannot be empty")
        if not 0 <= self.attempt_count <= self.max_attempts:
            raise ValidationError("execution event result attempt count is invalid")
        if not 1 <= self.max_attempts <= 10 or self.cycle < 0:
            raise ValidationError("execution event result bounds are invalid")
