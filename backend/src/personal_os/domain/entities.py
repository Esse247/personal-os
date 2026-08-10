from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum

from personal_os.domain.errors import InvalidTransitionError, ValidationError
from personal_os.domain.provenance import Provenance, require_aware


class IntentStatus(StrEnum):
    CAPTURED = "captured"
    NEEDS_CLARIFICATION = "needs_clarification"
    STRUCTURED = "structured"
    COMMITTED = "committed"
    DISMISSED = "dismissed"


class CommitmentStatus(StrEnum):
    CAPTURED = "captured"
    SCHEDULED = "scheduled"
    DELEGATED = "delegated"
    WAITING = "waiting"
    COMPLETED = "completed"
    DELIBERATELY_ABANDONED = "deliberately_abandoned"


class ProposalStatus(StrEnum):
    PROPOSED = "proposed"
    APPROVED = "approved"
    REJECTED = "rejected"
    SUPERSEDED = "superseded"
    EXPIRED = "expired"


class BlockStatus(StrEnum):
    CONFIRMED = "confirmed"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class ApprovalStatus(StrEnum):
    REQUESTED = "requested"
    APPROVED = "approved"
    REJECTED = "rejected"
    EXPIRED = "expired"
    CANCELLED = "cancelled"


class ClassificationStatus(StrEnum):
    CONFIRMED = "confirmed"
    CORRECTED = "corrected"
    REJECTED = "rejected"


@dataclass(slots=True)
class Intent:
    id: str
    user_id: str
    raw_text: str
    status: IntentStatus
    provenance: Provenance
    created_at: datetime
    title: str | None = None
    due_at: datetime | None = None
    duration_minutes: int | None = None
    clarification_question: str | None = None
    commitment_id: str | None = None
    version: int = 1

    def __post_init__(self) -> None:
        if not self.raw_text.strip():
            raise ValidationError("intent text is required")
        require_aware(self.created_at, "created_at")

    def need_clarification(self, question: str) -> None:
        if self.status not in {IntentStatus.CAPTURED, IntentStatus.NEEDS_CLARIFICATION}:
            raise InvalidTransitionError(f"cannot request clarification from {self.status}")
        if not question.strip():
            raise ValidationError("clarification question is required")
        self.status = IntentStatus.NEEDS_CLARIFICATION
        self.clarification_question = question
        self.version += 1

    def structure(self, *, title: str, due_at: datetime, duration_minutes: int) -> None:
        if self.status not in {IntentStatus.CAPTURED, IntentStatus.NEEDS_CLARIFICATION}:
            raise InvalidTransitionError(f"cannot structure intent from {self.status}")
        require_aware(due_at, "due_at")
        if not title.strip() or duration_minutes <= 0:
            raise ValidationError("structured title and positive duration are required")
        self.title = title
        self.due_at = due_at
        self.duration_minutes = duration_minutes
        self.clarification_question = None
        self.status = IntentStatus.STRUCTURED
        self.version += 1

    def commit(self, commitment_id: str) -> None:
        if self.status is not IntentStatus.STRUCTURED:
            raise InvalidTransitionError("only a structured intent can become committed")
        self.commitment_id = commitment_id
        self.status = IntentStatus.COMMITTED
        self.version += 1


@dataclass(slots=True)
class Commitment:
    id: str
    user_id: str
    title: str
    status: CommitmentStatus
    due_at: datetime
    duration_minutes: int
    provenance: Provenance
    created_at: datetime
    schedule_block_id: str | None = None
    waiting_reason: str | None = None
    review_at: datetime | None = None
    abandoned_reason: str | None = None
    version: int = 1

    def __post_init__(self) -> None:
        require_aware(self.due_at, "due_at")
        require_aware(self.created_at, "created_at")
        if self.duration_minutes <= 0:
            raise ValidationError("duration must be positive")

    def schedule(self, block_id: str) -> None:
        if self.status not in {CommitmentStatus.CAPTURED, CommitmentStatus.WAITING}:
            raise InvalidTransitionError(f"cannot schedule commitment from {self.status}")
        self.status = CommitmentStatus.SCHEDULED
        self.schedule_block_id = block_id
        self.waiting_reason = None
        self.review_at = None
        self.version += 1

    def wait(self, *, reason: str, review_at: datetime) -> None:
        if self.status in {
            CommitmentStatus.COMPLETED,
            CommitmentStatus.DELIBERATELY_ABANDONED,
        }:
            raise InvalidTransitionError(f"cannot wait from {self.status}")
        require_aware(review_at, "review_at")
        if not reason.strip():
            raise ValidationError("waiting requires a reason")
        self.status = CommitmentStatus.WAITING
        self.waiting_reason = reason
        self.review_at = review_at
        self.schedule_block_id = None
        self.version += 1

    def complete(self) -> None:
        if self.status not in {
            CommitmentStatus.SCHEDULED,
            CommitmentStatus.DELEGATED,
            CommitmentStatus.WAITING,
        }:
            raise InvalidTransitionError(f"cannot complete commitment from {self.status}")
        self.status = CommitmentStatus.COMPLETED
        self.version += 1

    def abandon(self, reason: str) -> None:
        if self.status in {
            CommitmentStatus.COMPLETED,
            CommitmentStatus.DELIBERATELY_ABANDONED,
        }:
            raise InvalidTransitionError(f"cannot abandon commitment from {self.status}")
        if not reason.strip():
            raise ValidationError("deliberate abandonment requires a reason")
        self.status = CommitmentStatus.DELIBERATELY_ABANDONED
        self.abandoned_reason = reason
        self.version += 1


@dataclass(slots=True)
class ScheduleProposal:
    id: str
    user_id: str
    commitment_id: str
    starts_at: datetime
    ends_at: datetime
    status: ProposalStatus
    rationale: str
    input_snapshot_hash: str
    revision: int
    created_at: datetime
    provenance: Provenance
    calendar_provider_id: str
    calendar_snapshot_version: str
    supersedes_id: str | None = None
    version: int = 1

    def __post_init__(self) -> None:
        require_aware(self.starts_at, "starts_at")
        require_aware(self.ends_at, "ends_at")
        if self.ends_at <= self.starts_at:
            raise ValidationError("proposal end must be after start")
        if len(self.input_snapshot_hash) != 64 or any(
            value not in "0123456789abcdef" for value in self.input_snapshot_hash.casefold()
        ):
            raise ValidationError("proposal snapshot hash must be SHA-256 hex")
        if not self.calendar_provider_id.strip() or not self.calendar_snapshot_version.strip():
            raise ValidationError("proposal calendar snapshot binding is required")

    def approve(self, expected_version: int) -> None:
        self._require_current(expected_version)
        if self.status is not ProposalStatus.PROPOSED:
            raise InvalidTransitionError(f"cannot approve proposal from {self.status}")
        self.status = ProposalStatus.APPROVED
        self.version += 1

    def reject(self, expected_version: int) -> None:
        self._require_current(expected_version)
        if self.status is not ProposalStatus.PROPOSED:
            raise InvalidTransitionError(f"cannot reject proposal from {self.status}")
        self.status = ProposalStatus.REJECTED
        self.version += 1

    def supersede(self, expected_version: int) -> None:
        self._require_current(expected_version)
        if self.status is not ProposalStatus.PROPOSED:
            raise InvalidTransitionError(f"cannot supersede proposal from {self.status}")
        self.status = ProposalStatus.SUPERSEDED
        self.version += 1

    def _require_current(self, expected_version: int) -> None:
        from personal_os.domain.errors import ConflictError

        if self.version != expected_version:
            raise ConflictError("proposal version is stale")


@dataclass(frozen=True, slots=True)
class ScheduleBlock:
    id: str
    user_id: str
    commitment_id: str
    starts_at: datetime
    ends_at: datetime
    status: BlockStatus
    created_at: datetime

    def __post_init__(self) -> None:
        require_aware(self.starts_at, "starts_at")
        require_aware(self.ends_at, "ends_at")
        if self.ends_at <= self.starts_at:
            raise ValidationError("block end must be after start")


@dataclass(frozen=True, slots=True)
class Approval:
    id: str
    user_id: str
    requester_id: str
    approver_id: str
    proposal_id: str
    permission: str
    action_level: int
    environment: str
    target_type: str
    target_id: str
    input_snapshot_hash: str
    calendar_provider_id: str
    calendar_snapshot_version: str
    provider_id: str
    on_behalf_of_id: str
    disclosed_data: str
    audience: str
    reversible: bool
    expected_consequence: str
    status: ApprovalStatus
    action_digest: str
    proposal_version: int
    commitment_version: int
    policy_version: str
    expires_at: datetime
    nonce: str
    idempotency_key: str
    created_at: datetime
    consumed_at: datetime | None = None

    def __post_init__(self) -> None:
        require_aware(self.expires_at, "expires_at")
        require_aware(self.created_at, "created_at")
        if self.consumed_at is not None:
            require_aware(self.consumed_at, "consumed_at")
        if self.expires_at <= self.created_at:
            raise ValidationError("approval must expire after it is created")
        if self.requester_id == self.approver_id:
            raise ValidationError("approval requester cannot self-approve")
        if self.action_level not in {0, 1, 2, 3, 4, 5}:
            raise ValidationError("approval action level is invalid")
        for value in (
            self.provider_id,
            self.on_behalf_of_id,
            self.disclosed_data,
            self.audience,
            self.expected_consequence,
            self.input_snapshot_hash,
            self.calendar_provider_id,
            self.calendar_snapshot_version,
        ):
            if not value.strip():
                raise ValidationError("approval binding fields cannot be empty")
        if len(self.input_snapshot_hash) != 64 or any(
            value not in "0123456789abcdef" for value in self.input_snapshot_hash.casefold()
        ):
            raise ValidationError("approval snapshot hash must be SHA-256 hex")


@dataclass(frozen=True, slots=True)
class WorldFact:
    id: str
    user_id: str
    fact_type: str
    label: str
    occurs_at: datetime
    provenance: Provenance
    created_at: datetime

    def __post_init__(self) -> None:
        require_aware(self.occurs_at, "occurs_at")


@dataclass(frozen=True, slots=True)
class Project:
    id: str
    user_id: str
    name: str
    status: str
    is_primary: bool
    created_at: datetime


@dataclass(frozen=True, slots=True)
class FinancialTransaction:
    id: str
    user_id: str
    household_id: str
    project_id: str | None
    merchant: str
    memo: str
    amount_minor: int
    currency: str
    posted_at: datetime
    provenance: Provenance
    created_at: datetime

    def __post_init__(self) -> None:
        require_aware(self.posted_at, "posted_at")
        if len(self.currency) != 3 or not self.currency.isalpha():
            raise ValidationError("currency must be a three-letter ISO code")


@dataclass(frozen=True, slots=True)
class TransactionClassification:
    id: str
    transaction_id: str
    category: str
    rule_id: str
    confidence: float
    status: ClassificationStatus
    provenance: Provenance
    created_at: datetime

    def __post_init__(self) -> None:
        if not 0 <= self.confidence <= 1:
            raise ValidationError("classification confidence must be between 0 and 1")


@dataclass(frozen=True, slots=True)
class AuditEvent:
    id: str
    user_id: str
    action: str
    entity_type: str
    entity_id: str
    correlation_id: str
    occurred_at: datetime
    outcome: str
    source_type: str
    source_identifier: str
    actor_id: str
    on_behalf_of_id: str | None
    entity_version: int
    causation_id: str
    policy_result: str
    capability_mode: str
    summary: str
    approval_id: str | None = None
    tool_reference: str | None = None
    agent_reference: str | None = None
    details: dict[str, str | int | float | bool | None] = field(default_factory=dict)

    def __post_init__(self) -> None:
        require_aware(self.occurred_at, "occurred_at")
        for value in (
            self.source_identifier,
            self.actor_id,
            self.causation_id,
            self.policy_result,
            self.capability_mode,
        ):
            if not value.strip():
                raise ValidationError("audit metadata fields cannot be empty")
        if self.entity_version < 0:
            raise ValidationError("audit entity version cannot be negative")


@dataclass(frozen=True, slots=True)
class CommandReceipt:
    idempotency_key: str
    user_id: str
    command_type: str
    request_digest: str
    created_at: datetime
    intent_id: str | None = None
    commitment_id: str | None = None
    proposal_id: str | None = None
    replacement_proposal_id: str | None = None

    def __post_init__(self) -> None:
        require_aware(self.created_at, "created_at")
        for value in (
            self.idempotency_key,
            self.user_id,
            self.command_type,
            self.request_digest,
        ):
            if not value.strip():
                raise ValidationError("command receipt fields cannot be empty")


@dataclass(frozen=True, slots=True)
class ConsentGrant:
    id: str
    grantor_user_id: str
    grantee_user_id: str
    resource_type: str
    resource_id: str
    permissions: frozenset[str]
    purpose: str
    issued_at: datetime
    expires_at: datetime
    provenance: Provenance
    revoked_at: datetime | None = None

    def __post_init__(self) -> None:
        require_aware(self.issued_at, "issued_at")
        require_aware(self.expires_at, "expires_at")
        if self.revoked_at is not None:
            require_aware(self.revoked_at, "revoked_at")
            if self.revoked_at < self.issued_at:
                raise ValidationError("consent grant cannot be revoked before issue")
        if self.expires_at <= self.issued_at:
            raise ValidationError("consent grant must expire after issue")
        if not self.permissions or not self.purpose.strip():
            raise ValidationError("consent grant requires permissions and purpose")

    def permits(
        self,
        *,
        grantee_user_id: str,
        resource_type: str,
        resource_id: str,
        permission: str,
        purpose: str,
        at: datetime,
    ) -> bool:
        require_aware(at, "at")
        return (
            self.grantee_user_id == grantee_user_id
            and self.resource_type == resource_type
            and self.resource_id == resource_id
            and permission in self.permissions
            and self.purpose == purpose
            and self.issued_at <= at < self.expires_at
            and (self.revoked_at is None or at < self.revoked_at)
        )
