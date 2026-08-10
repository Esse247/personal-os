from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from personal_os.domain.actions import ActionLevel, ToolActionDeclaration
from personal_os.domain.entities import (
    Approval,
    ApprovalStatus,
    Commitment,
    CommitmentStatus,
    Intent,
    IntentStatus,
)
from personal_os.domain.errors import InvalidTransitionError, ValidationError
from personal_os.domain.provenance import (
    ConfirmationStatus,
    Provenance,
    Sensitivity,
    SourceType,
)

NOW = datetime(2026, 8, 10, 8, 0, tzinfo=UTC)


def provenance(confidence: float = 1.0) -> Provenance:
    return Provenance(
        source_type=SourceType.USER_STATED,
        source_identifier="test:user-statement",
        observed_at=NOW,
        recorded_at=NOW,
        confidence=confidence,
        confirmation_status=ConfirmationStatus.CONFIRMED,
        sensitivity=Sensitivity.PERSONAL,
        actor_id="user-1",
        data_subject_id="user-1",
        controller_id="user-1",
        correlation_id="test-correlation",
    )


def commitment() -> Commitment:
    return Commitment(
        id="commitment-1",
        user_id="user-1",
        title="Arrange a haircut",
        status=CommitmentStatus.CAPTURED,
        due_at=NOW + timedelta(days=30),
        duration_minutes=60,
        provenance=provenance(),
        created_at=NOW,
    )


def test_provenance_rejects_invalid_confidence_and_naive_time() -> None:
    with pytest.raises(ValidationError, match="confidence"):
        provenance(1.01)
    with pytest.raises(ValidationError, match="timezone-aware"):
        Provenance(
            source_type=SourceType.SYSTEM_INFERRED,
            source_identifier="test",
            observed_at=datetime(2026, 8, 10),
            recorded_at=NOW,
            confidence=0.8,
            confirmation_status=ConfirmationStatus.UNCONFIRMED,
            sensitivity=Sensitivity.PERSONAL,
            actor_id="system",
            data_subject_id="user-1",
            controller_id="user-1",
            correlation_id="test-correlation",
        )


def test_intent_requires_clarification_before_structure() -> None:
    intent = Intent(
        id="intent-1",
        user_id="user-1",
        raw_text="Book something next month",
        status=IntentStatus.CAPTURED,
        provenance=provenance(),
        created_at=NOW,
    )
    intent.need_clarification("What should be arranged?")
    assert intent.status is IntentStatus.NEEDS_CLARIFICATION
    assert intent.commitment_id is None
    intent.structure(
        title="Arrange a haircut", due_at=NOW + timedelta(days=30), duration_minutes=60
    )
    intent.commit("commitment-1")
    assert intent.status is IntentStatus.COMMITTED
    with pytest.raises(InvalidTransitionError):
        intent.need_clarification("Too late")


def test_commitment_has_explicit_dispositions_and_no_silent_terminal_mutation() -> None:
    item = commitment()
    item.schedule("block-1")
    assert item.status is CommitmentStatus.SCHEDULED
    item.complete()
    assert item.status is CommitmentStatus.COMPLETED
    with pytest.raises(InvalidTransitionError):
        item.abandon("hide it")

    waiting = commitment()
    waiting.wait(reason="User rejected the proposal", review_at=NOW + timedelta(days=7))
    assert waiting.status is CommitmentStatus.WAITING
    waiting.abandon("No longer wanted")
    assert waiting.status is CommitmentStatus.DELIBERATELY_ABANDONED


def test_approval_requires_future_expiry() -> None:
    with pytest.raises(ValidationError, match="expire"):
        Approval(
            id="approval-1",
            user_id="user-1",
            requester_id="chief-of-staff-system",
            approver_id="user-1",
            proposal_id="proposal-1",
            permission="schedule.proposal.decide.own",
            action_level=3,
            environment="development-mock",
            target_type="schedule_proposal",
            target_id="proposal-1",
            input_snapshot_hash="b" * 64,
            calendar_provider_id="calendar-mock",
            calendar_snapshot_version="v1",
            provider_id="internal:none",
            on_behalf_of_id="user-1",
            disclosed_data="none",
            audience="local user",
            reversible=True,
            expected_consequence="schedule one internal block",
            status=ApprovalStatus.APPROVED,
            action_digest="a" * 64,
            proposal_version=1,
            commitment_version=1,
            policy_version="v1",
            expires_at=NOW,
            nonce="nonce",
            idempotency_key="idempotency",
            created_at=NOW,
        )


def test_approval_requester_cannot_self_approve() -> None:
    with pytest.raises(ValidationError, match="self-approve"):
        Approval(
            id="approval-2",
            user_id="user-1",
            requester_id="user-1",
            approver_id="user-1",
            proposal_id="proposal-1",
            permission="schedule.proposal.decide.own",
            action_level=3,
            environment="development-mock",
            target_type="schedule_proposal",
            target_id="proposal-1",
            input_snapshot_hash="b" * 64,
            calendar_provider_id="calendar-mock",
            calendar_snapshot_version="v1",
            provider_id="internal:none",
            on_behalf_of_id="user-1",
            disclosed_data="none",
            audience="local user",
            reversible=True,
            expected_consequence="schedule one internal block",
            status=ApprovalStatus.APPROVED,
            action_digest="a" * 64,
            proposal_version=1,
            commitment_version=1,
            policy_version="v1",
            expires_at=NOW + timedelta(minutes=15),
            nonce="nonce",
            idempotency_key="idempotency",
            created_at=NOW,
        )


def test_tool_action_declaration_requires_every_execution_control() -> None:
    declaration = ToolActionDeclaration(
        permission="schedule.block.create.own",
        action_level=ActionLevel.LEVEL_3,
        allowed_environment="development-mock",
        input_sensitivity="personal",
        output_sensitivity="personal",
        reversible=True,
        idempotency_behavior="one block per decision key",
        required_approval="exact proposal revision",
        expected_evidence="block and audit event",
        retry_policy="no automatic retry",
        recovery_path="cancel internal block",
        data_recipient="local user only",
        disclosure_purpose="create an approved internal block",
    )
    assert declaration.reversible
    with pytest.raises(ValidationError, match="recovery_path"):
        ToolActionDeclaration(
            permission="schedule.block.create.own",
            action_level=ActionLevel.LEVEL_3,
            allowed_environment="development-mock",
            input_sensitivity="personal",
            output_sensitivity="personal",
            reversible=True,
            idempotency_behavior="unique key",
            required_approval="exact revision",
            expected_evidence="audit",
            retry_policy="none",
            recovery_path="",
            data_recipient="local user only",
            disclosure_purpose="test validation",
        )
