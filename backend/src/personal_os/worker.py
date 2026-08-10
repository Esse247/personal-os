from __future__ import annotations

from dataclasses import dataclass

from personal_os.application.policy import AuthContext, FoundationPolicy, ResourceRef
from personal_os.domain.errors import ProhibitedCapabilityError


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
