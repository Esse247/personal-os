from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime

from personal_os.domain.entities import ConsentGrant
from personal_os.domain.errors import AuthorizationError


@dataclass(frozen=True, slots=True)
class AuthContext:
    principal_id: str
    purpose: str
    delegation_id: str | None = None
    environment: str = "development"


@dataclass(frozen=True, slots=True)
class ResourceRef:
    resource_type: str
    resource_id: str
    owner_user_id: str
    sensitivity: str


@dataclass(frozen=True, slots=True)
class PolicyDecision:
    allowed: bool
    rule_id: str


class FoundationPolicy:
    """Deliberately narrow, default-deny Foundation v0.1 policy."""

    VERSION = "foundation-policy-v1"
    EXECUTION_WORKER_ID = "personal-os-worker"
    HANDLE_PERMISSION = "outbox.event.handle.internal.own"
    RECOVER_PERMISSION = "outbox.event.recover.internal.own"
    READ_EXECUTION_PERMISSION = "outbox.event.read.internal.own"
    KNOWN_PERMISSIONS = frozenset(
        {
            "intent.capture.own",
            "intent.read.own",
            "commitment.read.own",
            "commitment.transition.own",
            "schedule.proposal.read.own",
            "schedule.proposal.decide.own",
            "finance.transaction.read.own",
            "finance.transaction.categorise.own",
            "audit.read.authorized",
            "provider.model.interpret.mock.own",
            "provider.calendar.availability.read.mock.own",
            "provider.banking.transactions.read.synthetic.own",
            HANDLE_PERMISSION,
            RECOVER_PERMISSION,
            READ_EXECUTION_PERMISSION,
        }
    )

    def __init__(
        self,
        grants: tuple[ConsentGrant, ...] = (),
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        self.grants = grants
        self.clock = clock or (lambda: datetime.now(UTC))

    def decide(
        self,
        context: AuthContext,
        permission: str,
        resource: ResourceRef,
    ) -> PolicyDecision:
        if permission not in self.KNOWN_PERMISSIONS:
            return PolicyDecision(False, "default-deny-unknown-permission")
        if permission == self.HANDLE_PERMISSION:
            if (
                context.principal_id == self.EXECUTION_WORKER_ID
                and context.delegation_id == resource.owner_user_id
                and context.environment in {"development", "test"}
                and context.purpose == "deliver committed internal event"
            ):
                return PolicyDecision(True, "execution-worker-scope-v1")
            return PolicyDecision(False, "default-deny-worker-scope")
        if permission == self.RECOVER_PERMISSION:
            if (
                context.principal_id == resource.owner_user_id
                and context.environment in {"development", "test"}
                and context.purpose == "recover failed internal event"
            ):
                return PolicyDecision(True, "execution-owner-recovery-v1")
            return PolicyDecision(False, "default-deny-recovery-scope")
        if permission == self.READ_EXECUTION_PERMISSION:
            if (
                context.principal_id == resource.owner_user_id
                and context.environment in {"development", "test"}
                and context.purpose == "read local execution state"
            ):
                return PolicyDecision(True, "execution-owner-read-v1")
            return PolicyDecision(False, "default-deny-execution-read-scope")
        if context.principal_id == resource.owner_user_id:
            return PolicyDecision(True, "owner-scope-v1")
        for grant in self.grants:
            if grant.grantor_user_id != resource.owner_user_id:
                continue
            if grant.permits(
                grantee_user_id=context.principal_id,
                resource_type=resource.resource_type,
                resource_id=resource.resource_id,
                permission=permission,
                purpose=context.purpose,
                at=self.clock(),
            ):
                return PolicyDecision(True, f"explicit-consent-grant:{grant.id}")
        return PolicyDecision(False, "default-deny-cross-person")

    def authorize(
        self,
        context: AuthContext,
        permission: str,
        resource: ResourceRef,
    ) -> str:
        decision = self.decide(context, permission, resource)
        if not decision.allowed:
            # A non-enumerating error prevents resource existence disclosure.
            raise AuthorizationError("resource not found")
        return decision.rule_id
