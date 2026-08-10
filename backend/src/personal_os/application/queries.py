from __future__ import annotations

from collections.abc import Callable
from dataclasses import asdict
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from personal_os.application.policy import AuthContext, FoundationPolicy, ResourceRef
from personal_os.domain.entities import AuditEvent
from personal_os.domain.errors import AuthorizationError, NotFoundError
from personal_os.domain.provenance import SourceType
from personal_os.ports.repositories import UnitOfWork

UnitOfWorkFactory = Callable[[], UnitOfWork]


def iso(value: datetime | None) -> str | None:
    return value.isoformat() if value else None


class DashboardQuery:
    def __init__(
        self,
        uow_factory: UnitOfWorkFactory,
        policy: FoundationPolicy | None = None,
        provider_mode: str = "mock",
    ) -> None:
        self.uow_factory = uow_factory
        self.policy = policy or FoundationPolicy()
        self.provider_mode = provider_mode

    def load(self, user_id: str) -> dict[str, Any]:
        context = AuthContext(user_id, "render personal dashboard")
        with self.uow_factory() as uow:
            self.policy.authorize(
                context,
                "commitment.read.own",
                ResourceRef("dashboard", user_id, user_id, "personal"),
            )
            self.policy.authorize(
                context,
                "finance.transaction.read.own",
                ResourceRef("finance_dashboard", user_id, user_id, "financial"),
            )
            self.policy.authorize(
                context,
                "audit.read.authorized",
                ResourceRef("audit_dashboard", user_id, user_id, "personal"),
            )
            commitments = uow.commitments.list_for_user(user_id)
            proposals = uow.proposals.list_for_user(user_id)
            blocks = uow.blocks.list_for_user(user_id)
            projects = uow.projects.list_for_user(user_id)
            transactions = uow.transactions.list_for_user(user_id)
            events = uow.audit.list_for_user(user_id, 40)
            approvals = uow.approvals.list_for_user(user_id)

            transaction_views = []
            for transaction in transactions:
                classification = uow.classifications.latest_for_transaction(transaction.id)
                transaction_views.append(
                    {
                        "id": transaction.id,
                        "merchant": transaction.merchant,
                        "memo": transaction.memo,
                        "amount_minor": transaction.amount_minor,
                        "currency": transaction.currency,
                        "posted_at": iso(transaction.posted_at),
                        "project_id": transaction.project_id,
                        "source_type": transaction.provenance.source_type.value,
                        "source_identifier": transaction.provenance.source_identifier,
                        "confidence": transaction.provenance.confidence,
                        "category": classification.category if classification else "Uncategorised",
                        "category_confidence": classification.confidence
                        if classification
                        else None,
                        "category_rule": classification.rule_id if classification else None,
                    }
                )

            return {
                "mode": {
                    "environment": "LOCAL",
                    "providers": self.provider_mode.upper(),
                    "data": "SYNTHETIC",
                    "identity": "DEVELOPMENT PERSONA",
                },
                "now": {
                    "headline": "Choose deliberately, then leave room",
                    "detail": (
                        "No minute-by-minute optimisation. Proposals preserve buffers "
                        "and await you."
                    ),
                },
                "today": {
                    "date": "2026-08-10",
                    "scheduled_count": len(blocks),
                    "protected_unstructured_minutes": 120,
                },
                "primary_project": next(
                    (
                        {"id": item.id, "name": item.name, "status": item.status}
                        for item in projects
                        if item.is_primary
                    ),
                    None,
                ),
                "projects": [
                    {"id": item.id, "name": item.name, "status": item.status} for item in projects
                ],
                "commitments": [
                    {
                        "id": item.id,
                        "title": item.title,
                        "status": item.status.value,
                        "due_at": iso(item.due_at),
                        "duration_minutes": item.duration_minutes,
                        "version": item.version,
                        "source_type": item.provenance.source_type.value,
                        "source_identifier": item.provenance.source_identifier,
                        "confidence": item.provenance.confidence,
                        "input_references": item.provenance.input_references,
                    }
                    for item in commitments
                ],
                "proposals": [
                    {
                        "id": item.id,
                        "commitment_id": item.commitment_id,
                        "starts_at": iso(item.starts_at),
                        "ends_at": iso(item.ends_at),
                        "status": item.status.value,
                        "rationale": item.rationale,
                        "revision": item.revision,
                        "version": item.version,
                        "supersedes_id": item.supersedes_id,
                        "calendar_provider_id": item.calendar_provider_id,
                        "calendar_snapshot_version": item.calendar_snapshot_version,
                    }
                    for item in proposals
                ],
                "schedule": [
                    {
                        "id": item.id,
                        "commitment_id": item.commitment_id,
                        "starts_at": iso(item.starts_at),
                        "ends_at": iso(item.ends_at),
                        "status": item.status.value,
                    }
                    for item in blocks
                ],
                "transactions": transaction_views,
                "approvals": [
                    {
                        "id": item.id,
                        "proposal_id": item.proposal_id,
                        "status": item.status.value,
                        "created_at": iso(item.created_at),
                    }
                    for item in approvals
                ],
                "activity": [
                    {
                        "id": event.id,
                        "action": event.action,
                        "entity_type": event.entity_type,
                        "entity_id": event.entity_id,
                        "correlation_id": event.correlation_id,
                        "occurred_at": iso(event.occurred_at),
                        "outcome": event.outcome,
                        "source_type": event.source_type,
                        "source_identifier": event.source_identifier,
                        "actor_id": event.actor_id,
                        "on_behalf_of_id": event.on_behalf_of_id,
                        "entity_version": event.entity_version,
                        "causation_id": event.causation_id,
                        "policy_result": event.policy_result,
                        "capability_mode": event.capability_mode,
                        "approval_id": event.approval_id,
                        "summary": event.summary,
                        "details": event.details,
                    }
                    for event in events
                ],
                "system_status": {
                    "api": "implemented",
                    "persistence": "implemented · local",
                    "model": "mocked · deterministic",
                    "calendar": "mocked · read only",
                    "banking": "mocked · synthetic fixture",
                    "external_actions": "prohibited",
                },
            }

    def transaction(self, user_id: str, transaction_id: str) -> dict[str, Any]:
        context = AuthContext(user_id, "view financial transaction")
        with self.uow_factory() as uow:
            transaction = uow.transactions.get(transaction_id)
            if transaction is None:
                raise NotFoundError("transaction not found")
            resource = ResourceRef(
                "financial_transaction",
                transaction.id,
                transaction.user_id,
                "financial",
            )
            decision = self.policy.decide(context, "finance.transaction.read.own", resource)
            if not decision.allowed:
                uow.audit.append(
                    AuditEvent(
                        id=str(uuid4()),
                        user_id=user_id,
                        action="authorization.denied",
                        entity_type="financial_transaction",
                        entity_id="protected-resource",
                        correlation_id=str(uuid4()),
                        occurred_at=datetime.now(UTC),
                        outcome="denied",
                        source_type=SourceType.USER_STATED.value,
                        source_identifier="authorization-request:financial-transaction",
                        actor_id=user_id,
                        on_behalf_of_id=None,
                        entity_version=0,
                        causation_id=str(uuid4()),
                        policy_result=f"denied:{decision.rule_id}",
                        capability_mode="local-mock-synthetic",
                        summary="A cross-person financial-resource request was denied.",
                        details={"policy_rule": decision.rule_id},
                    )
                )
                uow.commit()
                raise AuthorizationError("resource not found")
            classification = uow.classifications.latest_for_transaction(transaction.id)
            return {
                "id": transaction.id,
                "merchant": transaction.merchant,
                "memo": transaction.memo,
                "amount_minor": transaction.amount_minor,
                "currency": transaction.currency,
                "posted_at": iso(transaction.posted_at),
                "source": transaction.provenance.to_dict(),
                "classification": asdict(classification) if classification else None,
            }
