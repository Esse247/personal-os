from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from personal_os.adapters.providers.mock import (
    AlternativeDeterministicMockModelProvider,
    AlternativeMockCalendarProvider,
    DeterministicMockCalendarProvider,
    DeterministicMockModelProvider,
)
from personal_os.application.policy import AuthContext, FoundationPolicy, ResourceRef
from personal_os.config import Settings
from personal_os.domain.entities import ConsentGrant
from personal_os.domain.errors import AuthorizationError, ProhibitedCapabilityError
from personal_os.domain.provenance import (
    ConfirmationStatus,
    Provenance,
    Sensitivity,
    SourceType,
)
from personal_os.ports.providers import ProviderRequestContext
from personal_os.worker import FoundationWorker, JobEnvelope

NOW = datetime(2026, 8, 10, 8, 0, tzinfo=UTC)


def consent_grant(*, revoked: bool = False) -> ConsentGrant:
    return ConsentGrant(
        id="grant-1",
        grantor_user_id="user-b",
        grantee_user_id="user-a",
        resource_type="transaction",
        resource_id="t-b",
        permissions=frozenset({"finance.transaction.read.own"}),
        purpose="read shared invoice",
        issued_at=NOW,
        expires_at=datetime(2026, 8, 11, tzinfo=UTC),
        revoked_at=NOW if revoked else None,
        provenance=Provenance(
            source_type=SourceType.USER_STATED,
            source_identifier="test-consent",
            observed_at=NOW,
            recorded_at=NOW,
            confidence=1,
            confirmation_status=ConfirmationStatus.CONFIRMED,
            sensitivity=Sensitivity.PERSONAL,
            actor_id="user-b",
            data_subject_id="user-b",
            controller_id="user-b",
            correlation_id="test-correlation",
        ),
    )


def test_policy_defaults_to_deny_and_household_membership_is_not_authority() -> None:
    policy = FoundationPolicy()
    context = AuthContext("user-a", "read transaction")
    other_person_resource = ResourceRef("transaction", "t-b", "user-b", "financial")
    decision = policy.decide(context, "finance.transaction.read.own", other_person_resource)
    assert not decision.allowed
    assert decision.rule_id == "default-deny-cross-person"
    with pytest.raises(AuthorizationError):
        policy.authorize(context, "finance.transaction.read.own", other_person_resource)
    assert not policy.decide(context, "made.up.permission", other_person_resource).allowed


def test_explicit_consent_is_exactly_scoped_and_revocation_denies() -> None:
    resource = ResourceRef("transaction", "t-b", "user-b", "financial")
    context = AuthContext("user-a", "read shared invoice")
    policy = FoundationPolicy((consent_grant(),), clock=lambda: NOW)
    decision = policy.decide(context, "finance.transaction.read.own", resource)
    assert decision.allowed
    assert decision.rule_id == "explicit-consent-grant:grant-1"
    wrong_purpose = policy.decide(
        AuthContext("user-a", "analyse household spending"),
        "finance.transaction.read.own",
        resource,
    )
    assert not wrong_purpose.allowed
    revoked_policy = FoundationPolicy((consent_grant(revoked=True),), clock=lambda: NOW)
    assert not revoked_policy.decide(context, "finance.transaction.read.own", resource).allowed


def test_model_and_calendar_provider_substitution_preserves_canonical_behavior() -> None:
    provider_context = ProviderRequestContext(
        actor_id="chief-of-staff-system",
        on_behalf_of_id="user",
        correlation_id="provider-test-correlation",
        capability="model.intent.interpret",
        purpose="contract test",
        deadline_at=NOW + timedelta(seconds=30),
        idempotency_key="provider-test-key",
        task_type="intent_interpretation",
        risk="medium",
        privacy="personal",
    )
    text = "I need a haircut before the wedding next month."
    first = DeterministicMockModelProvider().interpret_intent(
        raw_text=text, context=provider_context
    )
    second = AlternativeDeterministicMockModelProvider().interpret_intent(
        raw_text=text, context=provider_context
    )
    assert (first.title, first.related_fact_label, first.missing_fields) == (
        second.title,
        second.related_fact_label,
        second.missing_fields,
    )

    before = datetime(2026, 9, 19, 14, 0, tzinfo=UTC).isoformat()
    calendar_a = DeterministicMockCalendarProvider().availability(
        user_id="user", before_iso=before, context=provider_context
    )
    calendar_b = AlternativeMockCalendarProvider().availability(
        user_id="user", before_iso=before, context=provider_context
    )
    assert calendar_a.slots == calendar_b.slots
    assert calendar_a.provenance == calendar_b.provenance


def test_foundation_configuration_fails_closed_for_live_or_remote_mode(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    with pytest.raises(ProhibitedCapabilityError):
        Settings(provider_mode="live").validate_foundation_mode()
    with pytest.raises(ProhibitedCapabilityError):
        Settings(provider_mode="null").validate_foundation_mode()
    with pytest.raises(ProhibitedCapabilityError):
        Settings(environment="production").validate_foundation_mode()
    with pytest.raises(ProhibitedCapabilityError):
        Settings(environment="unknown").validate_foundation_mode()
    with pytest.raises(ProhibitedCapabilityError):
        Settings(bind_host="0.0.0.0").validate_foundation_mode()
    with pytest.raises(ProhibitedCapabilityError):
        Settings(
            database_url="postgresql+psycopg://real:secret@remote.example/personal_os"
        ).validate_foundation_mode()
    monkeypatch.setenv("OPENAI_API_KEY", "synthetic-credential-shaped-value")
    with pytest.raises(ProhibitedCapabilityError, match="credential-bearing"):
        Settings().validate_foundation_mode()


def test_postgresql_configuration_requires_migrations_and_explicit_boolean(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    database_url = "postgresql+psycopg://personal_os:personal_os_local_only@localhost/personal_os"
    with pytest.raises(ProhibitedCapabilityError, match="Alembic bootstrap"):
        Settings(database_url=database_url).validate_foundation_mode()
    Settings(database_url=database_url, auto_initialize=False).validate_foundation_mode()

    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.setenv("PERSONAL_OS_AUTO_INITIALIZE", "sometimes")
    with pytest.raises(ProhibitedCapabilityError, match="explicit boolean"):
        Settings.from_environment()


def test_worker_is_policy_gated_and_cannot_expand_to_external_action() -> None:
    worker = FoundationWorker()
    allowed = JobEnvelope(
        id="job-1",
        action="foundation.simulate.noop",
        actor_id="user-a",
        owner_user_id="user-a",
        permission="commitment.read.own",
        purpose="simulate a bounded local job",
        environment="test",
        action_level=2,
        correlation_id="worker-test-correlation",
        idempotency_key="worker-test-idempotency",
        max_attempts=1,
    )
    assert worker.run(allowed)["policy_rule"] == "owner-scope-v1"
    prohibited = JobEnvelope(
        id="job-2",
        action="provider.external.execute",
        actor_id="user-a",
        owner_user_id="user-a",
        permission="commitment.read.own",
        purpose="attempt an external action",
        environment="test",
        action_level=4,
        correlation_id="worker-test-correlation",
        idempotency_key="worker-test-idempotency-2",
        max_attempts=1,
    )
    with pytest.raises(ProhibitedCapabilityError):
        worker.run(prohibited)
