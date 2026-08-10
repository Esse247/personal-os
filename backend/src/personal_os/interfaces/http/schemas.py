from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from personal_os.domain.entities import Commitment, Intent, ScheduleProposal


class ProvenanceView(BaseModel):
    source_type: str
    source_identifier: str
    observed_at: datetime
    recorded_at: datetime
    confidence: float
    confirmation_status: str
    sensitivity: str
    actor_id: str
    data_subject_id: str
    controller_id: str
    correlation_id: str
    input_references: tuple[str, ...]
    supersedes_reference: str | None


class IntentView(BaseModel):
    id: str
    raw_text: str
    status: str
    title: str | None
    due_at: datetime | None
    duration_minutes: int | None
    clarification_question: str | None
    commitment_id: str | None
    version: int
    provenance: ProvenanceView


class CommitmentView(BaseModel):
    id: str
    title: str
    status: str
    due_at: datetime
    duration_minutes: int
    schedule_block_id: str | None
    waiting_reason: str | None
    review_at: datetime | None
    version: int
    provenance: ProvenanceView


class ProposalView(BaseModel):
    id: str
    commitment_id: str
    starts_at: datetime
    ends_at: datetime
    status: str
    rationale: str
    revision: int
    version: int
    supersedes_id: str | None
    provenance: ProvenanceView
    calendar_provider_id: str
    calendar_snapshot_version: str


class CaptureRequest(BaseModel):
    text: str = Field(min_length=1, max_length=2000)


class CaptureResponse(BaseModel):
    intent: IntentView
    commitment: CommitmentView | None
    proposal: ProposalView | None


class DecisionRequest(BaseModel):
    decision: Literal["approve", "change", "reject"]
    requested_start: datetime | None = None


class DecisionResponse(BaseModel):
    proposal: ProposalView
    replacement: ProposalView | None
    commitment: CommitmentView


class DashboardResponse(BaseModel):
    model_config = ConfigDict(extra="allow")

    mode: dict[str, str]
    now: dict[str, Any]
    today: dict[str, Any]
    primary_project: dict[str, Any] | None
    projects: list[dict[str, Any]]
    commitments: list[dict[str, Any]]
    proposals: list[dict[str, Any]]
    schedule: list[dict[str, Any]]
    transactions: list[dict[str, Any]]
    approvals: list[dict[str, Any]]
    activity: list[dict[str, Any]]
    system_status: dict[str, str]


def provenance_view(entity: Intent) -> ProvenanceView:
    value = entity.provenance
    return ProvenanceView(
        source_type=value.source_type.value,
        source_identifier=value.source_identifier,
        observed_at=value.observed_at,
        recorded_at=value.recorded_at,
        confidence=value.confidence,
        confirmation_status=value.confirmation_status.value,
        sensitivity=value.sensitivity.value,
        actor_id=value.actor_id,
        data_subject_id=value.data_subject_id,
        controller_id=value.controller_id,
        correlation_id=value.correlation_id,
        input_references=value.input_references,
        supersedes_reference=value.supersedes_reference,
    )


def intent_view(entity: Intent) -> IntentView:
    return IntentView(
        id=entity.id,
        raw_text=entity.raw_text,
        status=entity.status.value,
        title=entity.title,
        due_at=entity.due_at,
        duration_minutes=entity.duration_minutes,
        clarification_question=entity.clarification_question,
        commitment_id=entity.commitment_id,
        version=entity.version,
        provenance=provenance_view(entity),
    )


def commitment_view(entity: Commitment | None) -> CommitmentView | None:
    if entity is None:
        return None
    return CommitmentView(
        id=entity.id,
        title=entity.title,
        status=entity.status.value,
        due_at=entity.due_at,
        duration_minutes=entity.duration_minutes,
        schedule_block_id=entity.schedule_block_id,
        waiting_reason=entity.waiting_reason,
        review_at=entity.review_at,
        version=entity.version,
        provenance=ProvenanceView(
            source_type=entity.provenance.source_type.value,
            source_identifier=entity.provenance.source_identifier,
            observed_at=entity.provenance.observed_at,
            recorded_at=entity.provenance.recorded_at,
            confidence=entity.provenance.confidence,
            confirmation_status=entity.provenance.confirmation_status.value,
            sensitivity=entity.provenance.sensitivity.value,
            actor_id=entity.provenance.actor_id,
            data_subject_id=entity.provenance.data_subject_id,
            controller_id=entity.provenance.controller_id,
            correlation_id=entity.provenance.correlation_id,
            input_references=entity.provenance.input_references,
            supersedes_reference=entity.provenance.supersedes_reference,
        ),
    )


def proposal_view(entity: ScheduleProposal | None) -> ProposalView | None:
    if entity is None:
        return None
    return ProposalView(
        id=entity.id,
        commitment_id=entity.commitment_id,
        starts_at=entity.starts_at,
        ends_at=entity.ends_at,
        status=entity.status.value,
        rationale=entity.rationale,
        revision=entity.revision,
        version=entity.version,
        supersedes_id=entity.supersedes_id,
        calendar_provider_id=entity.calendar_provider_id,
        calendar_snapshot_version=entity.calendar_snapshot_version,
        provenance=ProvenanceView(
            source_type=entity.provenance.source_type.value,
            source_identifier=entity.provenance.source_identifier,
            observed_at=entity.provenance.observed_at,
            recorded_at=entity.provenance.recorded_at,
            confidence=entity.provenance.confidence,
            confirmation_status=entity.provenance.confirmation_status.value,
            sensitivity=entity.provenance.sensitivity.value,
            actor_id=entity.provenance.actor_id,
            data_subject_id=entity.provenance.data_subject_id,
            controller_id=entity.provenance.controller_id,
            correlation_id=entity.provenance.correlation_id,
            input_references=entity.provenance.input_references,
            supersedes_reference=entity.provenance.supersedes_reference,
        ),
    )
