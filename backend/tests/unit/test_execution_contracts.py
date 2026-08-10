from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime, timedelta

import pytest

from personal_os.application.policy import AuthContext, FoundationPolicy, ResourceRef
from personal_os.config import DEMO_USER_ID, OTHER_USER_ID
from personal_os.domain.errors import ValidationError
from personal_os.domain.events import InternalEventType, OutboxEvent, OutboxStatus


def event() -> OutboxEvent:
    occurred_at = datetime(2026, 8, 10, 8, 0, tzinfo=UTC)
    return OutboxEvent(
        id="unit-outbox-event",
        event_type=InternalEventType.INTENT_CAPTURED,
        schema_version=1,
        aggregate_type="intent",
        aggregate_id="unit-intent",
        aggregate_version=1,
        owner_user_id=DEMO_USER_ID,
        controller_id=DEMO_USER_ID,
        data_subject_id=DEMO_USER_ID,
        actor_id=DEMO_USER_ID,
        on_behalf_of_id=None,
        sensitivity="personal",
        correlation_id="unit-execution-correlation",
        causation_id="unit-execution-causation",
        occurred_at=occurred_at,
        capability_mode="local-mock-synthetic",
        producer_key="unit-execution-producer-key",
        payload={"state": "captured"},
        available_at=occurred_at,
    )


def test_canonical_event_rejects_unredacted_keys_credentials_and_live_mode() -> None:
    with pytest.raises(ValidationError, match="non-allowlisted"):
        replace(event(), payload={"raw_text": "private source material"})
    with pytest.raises(ValidationError, match="sensitivity"):
        replace(event(), sensitivity="credential")
    with pytest.raises(ValidationError, match="local, mock, and synthetic"):
        replace(event(), capability_mode="live")


def test_outbox_state_requires_complete_current_lease_shape() -> None:
    with pytest.raises(ValidationError, match="complete lease"):
        replace(event(), status=OutboxStatus.PROCESSING)
    claimed = replace(
        event(),
        status=OutboxStatus.PROCESSING,
        attempt_count=1,
        lease_owner="personal-os-worker:unit",
        lease_token="unit-fencing-token",
        lease_expires_at=event().occurred_at + timedelta(seconds=30),
    )
    assert claimed.lease_token == "unit-fencing-token"
    with pytest.raises(ValidationError, match="cannot retain a lease"):
        replace(claimed, status=OutboxStatus.PENDING)


def test_execution_permissions_bind_server_worker_delegation_purpose_and_environment() -> None:
    policy = FoundationPolicy()
    resource = ResourceRef("outbox_event", "unit-event", DEMO_USER_ID, "personal")
    allowed = policy.decide(
        AuthContext(
            FoundationPolicy.EXECUTION_WORKER_ID,
            "deliver committed internal event",
            delegation_id=DEMO_USER_ID,
            environment="test",
        ),
        FoundationPolicy.HANDLE_PERMISSION,
        resource,
    )
    assert allowed.allowed and allowed.rule_id == "execution-worker-scope-v1"
    for context in (
        AuthContext(DEMO_USER_ID, "deliver committed internal event", environment="test"),
        AuthContext(
            FoundationPolicy.EXECUTION_WORKER_ID,
            "different purpose",
            delegation_id=DEMO_USER_ID,
            environment="test",
        ),
        AuthContext(
            FoundationPolicy.EXECUTION_WORKER_ID,
            "deliver committed internal event",
            delegation_id=OTHER_USER_ID,
            environment="test",
        ),
        AuthContext(
            FoundationPolicy.EXECUTION_WORKER_ID,
            "deliver committed internal event",
            delegation_id=DEMO_USER_ID,
            environment="production",
        ),
    ):
        assert not policy.decide(
            context,
            FoundationPolicy.HANDLE_PERMISSION,
            resource,
        ).allowed


def test_recovery_permission_is_owner_only_and_purpose_bound() -> None:
    policy = FoundationPolicy()
    resource = ResourceRef("outbox_event", "unit-event", DEMO_USER_ID, "personal")
    assert policy.decide(
        AuthContext(DEMO_USER_ID, "recover failed internal event", environment="test"),
        FoundationPolicy.RECOVER_PERMISSION,
        resource,
    ).allowed
    assert not policy.decide(
        AuthContext(OTHER_USER_ID, "recover failed internal event", environment="test"),
        FoundationPolicy.RECOVER_PERMISSION,
        resource,
    ).allowed
    assert not policy.decide(
        AuthContext(DEMO_USER_ID, "different purpose", environment="test"),
        FoundationPolicy.RECOVER_PERMISSION,
        resource,
    ).allowed


def test_execution_read_permission_is_owner_environment_and_purpose_bound() -> None:
    policy = FoundationPolicy()
    resource = ResourceRef("outbox_event", "owner-scoped-collection", DEMO_USER_ID, "personal")
    allowed = policy.decide(
        AuthContext(DEMO_USER_ID, "read local execution state", environment="test"),
        FoundationPolicy.READ_EXECUTION_PERMISSION,
        resource,
    )
    assert allowed.allowed and allowed.rule_id == "execution-owner-read-v1"
    for context in (
        AuthContext(OTHER_USER_ID, "read local execution state", environment="test"),
        AuthContext(DEMO_USER_ID, "different purpose", environment="test"),
        AuthContext(DEMO_USER_ID, "read local execution state", environment="production"),
    ):
        assert not policy.decide(
            context,
            FoundationPolicy.READ_EXECUTION_PERMISSION,
            resource,
        ).allowed
