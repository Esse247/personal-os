from __future__ import annotations

from typing import Protocol

from personal_os.domain.entities import (
    Approval,
    AuditEvent,
    CommandReceipt,
    Commitment,
    FinancialTransaction,
    Intent,
    Project,
    ScheduleBlock,
    ScheduleProposal,
    TransactionClassification,
    WorldFact,
)
from personal_os.domain.events import (
    ConsumerReceipt,
    InternalEffect,
    OutboxEvent,
    OutboxStatus,
    OutboxTransition,
)


class IntentRepository(Protocol):
    def add(self, entity: Intent) -> None: ...
    def get(self, entity_id: str) -> Intent | None: ...
    def list_for_user(self, user_id: str) -> list[Intent]: ...


class CommitmentRepository(Protocol):
    def add(self, entity: Commitment) -> None: ...
    def get(self, entity_id: str) -> Commitment | None: ...
    def list_for_user(self, user_id: str) -> list[Commitment]: ...


class ProposalRepository(Protocol):
    def add(self, entity: ScheduleProposal) -> None: ...
    def get(self, entity_id: str) -> ScheduleProposal | None: ...
    def list_for_user(self, user_id: str) -> list[ScheduleProposal]: ...


class BlockRepository(Protocol):
    def add(self, entity: ScheduleBlock) -> None: ...
    def list_for_user(self, user_id: str) -> list[ScheduleBlock]: ...


class CommandReceiptRepository(Protocol):
    def add(self, entity: CommandReceipt) -> None: ...
    def get(self, idempotency_key: str) -> CommandReceipt | None: ...
    def lock_key(self, idempotency_key: str) -> None: ...


class ApprovalRepository(Protocol):
    def add(self, entity: Approval) -> None: ...
    def find_by_idempotency_key(self, key: str) -> Approval | None: ...
    def list_for_user(self, user_id: str) -> list[Approval]: ...


class WorldFactRepository(Protocol):
    def add(self, entity: WorldFact) -> None: ...
    def find_confirmed_by_label(self, user_id: str, label: str) -> WorldFact | None: ...


class ProjectRepository(Protocol):
    def add(self, entity: Project) -> None: ...
    def primary_for_user(self, user_id: str) -> Project | None: ...
    def list_for_user(self, user_id: str) -> list[Project]: ...


class TransactionRepository(Protocol):
    def add(self, entity: FinancialTransaction) -> None: ...
    def get(self, entity_id: str) -> FinancialTransaction | None: ...
    def list_for_user(self, user_id: str) -> list[FinancialTransaction]: ...


class ClassificationRepository(Protocol):
    def add(self, entity: TransactionClassification) -> None: ...
    def latest_for_transaction(self, transaction_id: str) -> TransactionClassification | None: ...


class AuditRepository(Protocol):
    def append(self, entity: AuditEvent) -> None: ...
    def list_for_user(self, user_id: str, limit: int = 100) -> list[AuditEvent]: ...


class OutboxRepository(Protocol):
    def enqueue(self, event: OutboxEvent) -> None: ...
    def get(self, event_id: str) -> OutboxEvent | None: ...
    def claim_next(self, worker_id: str, lease_seconds: int) -> OutboxEvent | None: ...
    def mark_delivered(
        self,
        event_id: str,
        worker_id: str,
        lease_token: str,
        *,
        duplicate_suppressed: bool = False,
    ) -> OutboxEvent: ...
    def record_failure(
        self,
        event_id: str,
        worker_id: str,
        lease_token: str,
        failure_code: str,
        *,
        retryable: bool,
        policy_result: str,
    ) -> OutboxEvent: ...
    def recover(
        self,
        event_id: str,
        actor_id: str,
        reason: str,
        policy_result: str,
    ) -> OutboxEvent: ...
    def list_failed(self, owner_user_id: str) -> list[OutboxEvent]: ...
    def status_counts(self, owner_user_id: str) -> dict[OutboxStatus, int]: ...


class ConsumerReceiptRepository(Protocol):
    def add(self, receipt: ConsumerReceipt) -> None: ...
    def get(self, consumer_name: str, event_id: str) -> ConsumerReceipt | None: ...


class InternalEffectRepository(Protocol):
    def add(self, effect: InternalEffect) -> None: ...
    def get_for_event(self, consumer_name: str, event_id: str) -> InternalEffect | None: ...


class OutboxTransitionRepository(Protocol):
    def list_for_event(self, event_id: str) -> list[OutboxTransition]: ...


class UnitOfWork(Protocol):
    intents: IntentRepository
    commitments: CommitmentRepository
    proposals: ProposalRepository
    blocks: BlockRepository
    approvals: ApprovalRepository
    receipts: CommandReceiptRepository
    world_facts: WorldFactRepository
    projects: ProjectRepository
    transactions: TransactionRepository
    classifications: ClassificationRepository
    audit: AuditRepository
    outbox: OutboxRepository
    consumer_receipts: ConsumerReceiptRepository
    internal_effects: InternalEffectRepository
    outbox_transitions: OutboxTransitionRepository

    def __enter__(self) -> UnitOfWork: ...
    def __exit__(self, *args: object) -> None: ...
    def commit(self) -> None: ...
    def rollback(self) -> None: ...
