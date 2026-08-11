from __future__ import annotations

import json
from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from uuid import uuid4

from sqlalchemy import Engine, and_, desc, func, or_, select, update
from sqlalchemy.exc import DBAPIError, IntegrityError
from sqlalchemy.orm import Session, sessionmaker

from personal_os.adapters.persistence.models import (
    ApprovalRow,
    AuditEventRow,
    CommandReceiptRow,
    CommitmentRow,
    ConsumerReceiptRow,
    FinancialTransactionRow,
    IntentRow,
    InternalEffectRow,
    OutboxEventRow,
    OutboxTransitionRow,
    ProjectRow,
    ScheduleBlockRow,
    ScheduleProposalRow,
    TransactionClassificationRow,
    WorldFactRow,
)
from personal_os.domain.entities import (
    Approval,
    ApprovalStatus,
    AuditEvent,
    BlockStatus,
    ClassificationStatus,
    CommandReceipt,
    Commitment,
    CommitmentStatus,
    FinancialTransaction,
    Intent,
    IntentStatus,
    Project,
    ProposalStatus,
    ScheduleBlock,
    ScheduleProposal,
    TransactionClassification,
    WorldFact,
)
from personal_os.domain.errors import LockTimeoutError
from personal_os.domain.events import (
    ConsumerReceipt,
    InternalEffect,
    InternalEventType,
    OutboxEvent,
    OutboxStatus,
    OutboxTransition,
    OutboxTransitionType,
)
from personal_os.domain.provenance import ConfirmationStatus, Provenance
from personal_os.ports.repositories import (
    ApprovalRepository,
    AuditRepository,
    BlockRepository,
    ClassificationRepository,
    CommandReceiptRepository,
    CommitmentRepository,
    ConsumerReceiptRepository,
    IntentRepository,
    InternalEffectRepository,
    OutboxRepository,
    OutboxTransitionRepository,
    ProjectRepository,
    ProposalRepository,
    TransactionRepository,
    UnitOfWork,
    WorldFactRepository,
)

RECOVERY_LOCK_TIMEOUT_MS = 500


def _run_with_scoped_postgresql_lock_timeout[T](
    session: Session,
    operation: Callable[[], T],
) -> T:
    """Run one PostgreSQL lock operation with a bounded, non-leaking timeout."""
    previous_timeout = session.scalar(select(func.current_setting("lock_timeout")))
    if not isinstance(previous_timeout, str):  # pragma: no cover - PostgreSQL contract
        raise RuntimeError("database lock timeout setting is unavailable")
    try:
        with session.begin_nested():
            session.scalar(
                select(
                    func.set_config(
                        "lock_timeout",
                        f"{RECOVERY_LOCK_TIMEOUT_MS}ms",
                        True,
                    )
                )
            )
            result = operation()
            # SET LOCAL inside a released savepoint otherwise survives for the outer
            # transaction. Restore the exact prior value before releasing it.
            session.scalar(select(func.set_config("lock_timeout", previous_timeout, True)))
            return result
    except DBAPIError as exc:
        if getattr(exc.orig, "sqlstate", None) == "55P03":
            raise LockTimeoutError("recovery command is temporarily busy; retry") from exc
        raise


def aware(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    return value if value.tzinfo else value.replace(tzinfo=UTC)


def provenance_json(value: Provenance) -> str:
    return json.dumps(value.to_dict(), sort_keys=True)


def parse_provenance(value: str) -> Provenance:
    return Provenance.from_dict(json.loads(value))


class SqlIntentRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def add(self, entity: Intent) -> None:
        self.session.merge(
            IntentRow(
                id=entity.id,
                user_id=entity.user_id,
                raw_text=entity.raw_text,
                status=entity.status.value,
                provenance_json=provenance_json(entity.provenance),
                created_at=entity.created_at,
                title=entity.title,
                due_at=entity.due_at,
                duration_minutes=entity.duration_minutes,
                clarification_question=entity.clarification_question,
                commitment_id=entity.commitment_id,
                version=entity.version,
            )
        )

    def get(self, entity_id: str) -> Intent | None:
        row = self.session.get(IntentRow, entity_id)
        return self._map(row) if row else None

    def list_for_user(self, user_id: str) -> list[Intent]:
        rows = self.session.scalars(
            select(IntentRow)
            .where(IntentRow.user_id == user_id)
            .order_by(desc(IntentRow.created_at))
        )
        return [self._map(row) for row in rows]

    @staticmethod
    def _map(row: IntentRow) -> Intent:
        return Intent(
            id=row.id,
            user_id=row.user_id,
            raw_text=row.raw_text,
            status=IntentStatus(row.status),
            provenance=parse_provenance(row.provenance_json),
            created_at=aware(row.created_at),  # type: ignore[arg-type]
            title=row.title,
            due_at=aware(row.due_at),
            duration_minutes=row.duration_minutes,
            clarification_question=row.clarification_question,
            commitment_id=row.commitment_id,
            version=row.version,
        )


class SqlCommitmentRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def add(self, entity: Commitment) -> None:
        values = {
            "user_id": entity.user_id,
            "title": entity.title,
            "status": entity.status.value,
            "due_at": entity.due_at,
            "duration_minutes": entity.duration_minutes,
            "provenance_json": provenance_json(entity.provenance),
            "created_at": entity.created_at,
            "schedule_block_id": entity.schedule_block_id,
            "waiting_reason": entity.waiting_reason,
            "review_at": entity.review_at,
            "abandoned_reason": entity.abandoned_reason,
            "version": entity.version,
        }
        current = self.session.get(CommitmentRow, entity.id)
        if current is None:
            self.session.add(CommitmentRow(id=entity.id, **values))
            return
        if entity.version != current.version + 1:
            from personal_os.domain.errors import ConflictError

            raise ConflictError("commitment version is stale")
        result = self.session.execute(
            update(CommitmentRow)
            .where(CommitmentRow.id == entity.id, CommitmentRow.version == current.version)
            .values(**values)
            .execution_options(synchronize_session=False)
        )
        if getattr(result, "rowcount", 0) != 1:
            from personal_os.domain.errors import ConflictError

            raise ConflictError("commitment version changed concurrently")
        self.session.expire(current)

    def get(self, entity_id: str) -> Commitment | None:
        row = self.session.get(CommitmentRow, entity_id)
        return self._map(row) if row else None

    def list_for_user(self, user_id: str) -> list[Commitment]:
        rows = self.session.scalars(
            select(CommitmentRow)
            .where(CommitmentRow.user_id == user_id)
            .order_by(CommitmentRow.due_at)
        )
        return [self._map(row) for row in rows]

    @staticmethod
    def _map(row: CommitmentRow) -> Commitment:
        return Commitment(
            id=row.id,
            user_id=row.user_id,
            title=row.title,
            status=CommitmentStatus(row.status),
            due_at=aware(row.due_at),  # type: ignore[arg-type]
            duration_minutes=row.duration_minutes,
            provenance=parse_provenance(row.provenance_json),
            created_at=aware(row.created_at),  # type: ignore[arg-type]
            schedule_block_id=row.schedule_block_id,
            waiting_reason=row.waiting_reason,
            review_at=aware(row.review_at),
            abandoned_reason=row.abandoned_reason,
            version=row.version,
        )


class SqlProposalRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def add(self, entity: ScheduleProposal) -> None:
        values = {
            "user_id": entity.user_id,
            "commitment_id": entity.commitment_id,
            "starts_at": entity.starts_at,
            "ends_at": entity.ends_at,
            "status": entity.status.value,
            "rationale": entity.rationale,
            "input_snapshot_hash": entity.input_snapshot_hash,
            "revision": entity.revision,
            "created_at": entity.created_at,
            "provenance_json": provenance_json(entity.provenance),
            "calendar_provider_id": entity.calendar_provider_id,
            "calendar_snapshot_version": entity.calendar_snapshot_version,
            "supersedes_id": entity.supersedes_id,
            "version": entity.version,
        }
        current = self.session.get(ScheduleProposalRow, entity.id)
        if current is None:
            self.session.add(ScheduleProposalRow(id=entity.id, **values))
            return
        if entity.version != current.version + 1:
            from personal_os.domain.errors import ConflictError

            raise ConflictError("proposal version is stale")
        result = self.session.execute(
            update(ScheduleProposalRow)
            .where(
                ScheduleProposalRow.id == entity.id,
                ScheduleProposalRow.version == current.version,
            )
            .values(**values)
            .execution_options(synchronize_session=False)
        )
        if getattr(result, "rowcount", 0) != 1:
            from personal_os.domain.errors import ConflictError

            raise ConflictError("proposal version changed concurrently")
        self.session.expire(current)

    def get(self, entity_id: str) -> ScheduleProposal | None:
        row = self.session.get(ScheduleProposalRow, entity_id)
        return self._map(row) if row else None

    def list_for_user(self, user_id: str) -> list[ScheduleProposal]:
        rows = self.session.scalars(
            select(ScheduleProposalRow)
            .where(ScheduleProposalRow.user_id == user_id)
            .order_by(desc(ScheduleProposalRow.created_at))
        )
        return [self._map(row) for row in rows]

    @staticmethod
    def _map(row: ScheduleProposalRow) -> ScheduleProposal:
        return ScheduleProposal(
            id=row.id,
            user_id=row.user_id,
            commitment_id=row.commitment_id,
            starts_at=aware(row.starts_at),  # type: ignore[arg-type]
            ends_at=aware(row.ends_at),  # type: ignore[arg-type]
            status=ProposalStatus(row.status),
            rationale=row.rationale,
            input_snapshot_hash=row.input_snapshot_hash,
            revision=row.revision,
            created_at=aware(row.created_at),  # type: ignore[arg-type]
            provenance=parse_provenance(row.provenance_json),
            calendar_provider_id=row.calendar_provider_id,
            calendar_snapshot_version=row.calendar_snapshot_version,
            supersedes_id=row.supersedes_id,
            version=row.version,
        )


class SqlBlockRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def add(self, entity: ScheduleBlock) -> None:
        from personal_os.domain.errors import ConflictError

        bind = self.session.get_bind()
        if bind.dialect.name == "postgresql":
            # Serialize the overlap check and insert for one user's schedule. PostgreSQL
            # READ COMMITTED then observes a predecessor's commit before this SELECT.
            self.session.execute(
                select(func.pg_advisory_xact_lock(func.hashtextextended(entity.user_id, 0)))
            )
        conflict = self.session.scalar(
            select(ScheduleBlockRow.id)
            .where(
                ScheduleBlockRow.user_id == entity.user_id,
                ScheduleBlockRow.status == BlockStatus.CONFIRMED.value,
                ScheduleBlockRow.starts_at < entity.ends_at,
                ScheduleBlockRow.ends_at > entity.starts_at,
            )
            .limit(1)
        )
        if conflict is not None:
            raise ConflictError("schedule block conflicts with an existing confirmed block")
        self.session.add(
            ScheduleBlockRow(
                id=entity.id,
                user_id=entity.user_id,
                commitment_id=entity.commitment_id,
                starts_at=entity.starts_at,
                ends_at=entity.ends_at,
                status=entity.status.value,
                created_at=entity.created_at,
            )
        )

    def list_for_user(self, user_id: str) -> list[ScheduleBlock]:
        rows = self.session.scalars(
            select(ScheduleBlockRow)
            .where(ScheduleBlockRow.user_id == user_id)
            .order_by(ScheduleBlockRow.starts_at)
        )
        return [
            ScheduleBlock(
                id=row.id,
                user_id=row.user_id,
                commitment_id=row.commitment_id,
                starts_at=aware(row.starts_at),  # type: ignore[arg-type]
                ends_at=aware(row.ends_at),  # type: ignore[arg-type]
                status=BlockStatus(row.status),
                created_at=aware(row.created_at),  # type: ignore[arg-type]
            )
            for row in rows
        ]


class SqlCommandReceiptRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def add(self, entity: CommandReceipt) -> None:
        self.session.add(
            CommandReceiptRow(
                idempotency_key=entity.idempotency_key,
                user_id=entity.user_id,
                command_type=entity.command_type,
                request_digest=entity.request_digest,
                created_at=entity.created_at,
                intent_id=entity.intent_id,
                commitment_id=entity.commitment_id,
                proposal_id=entity.proposal_id,
                replacement_proposal_id=entity.replacement_proposal_id,
                outbox_event_id=entity.outbox_event_id,
                result_json=entity.result_json,
            )
        )

    def get(self, idempotency_key: str) -> CommandReceipt | None:
        row = self.session.get(CommandReceiptRow, idempotency_key)
        if row is None:
            return None
        return CommandReceipt(
            idempotency_key=row.idempotency_key,
            user_id=row.user_id,
            command_type=row.command_type,
            request_digest=row.request_digest,
            created_at=aware(row.created_at),  # type: ignore[arg-type]
            intent_id=row.intent_id,
            commitment_id=row.commitment_id,
            proposal_id=row.proposal_id,
            replacement_proposal_id=row.replacement_proposal_id,
            outbox_event_id=row.outbox_event_id,
            result_json=row.result_json,
        )

    def lock_key(self, idempotency_key: str) -> None:
        if not idempotency_key.strip():
            raise ValueError("idempotency key cannot be empty")
        if self.session.get_bind().dialect.name == "postgresql":
            _run_with_scoped_postgresql_lock_timeout(
                self.session,
                lambda: self.session.execute(
                    select(func.pg_advisory_xact_lock(func.hashtextextended(idempotency_key, 1)))
                ),
            )


class SqlApprovalRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def add(self, entity: Approval) -> None:
        self.session.add(
            ApprovalRow(
                id=entity.id,
                user_id=entity.user_id,
                requester_id=entity.requester_id,
                approver_id=entity.approver_id,
                proposal_id=entity.proposal_id,
                permission=entity.permission,
                action_level=entity.action_level,
                environment=entity.environment,
                target_type=entity.target_type,
                target_id=entity.target_id,
                input_snapshot_hash=entity.input_snapshot_hash,
                calendar_provider_id=entity.calendar_provider_id,
                calendar_snapshot_version=entity.calendar_snapshot_version,
                provider_id=entity.provider_id,
                on_behalf_of_id=entity.on_behalf_of_id,
                disclosed_data=entity.disclosed_data,
                audience=entity.audience,
                reversible=entity.reversible,
                expected_consequence=entity.expected_consequence,
                status=entity.status.value,
                action_digest=entity.action_digest,
                proposal_version=entity.proposal_version,
                commitment_version=entity.commitment_version,
                policy_version=entity.policy_version,
                expires_at=entity.expires_at,
                nonce=entity.nonce,
                idempotency_key=entity.idempotency_key,
                created_at=entity.created_at,
                consumed_at=entity.consumed_at,
            )
        )

    def find_by_idempotency_key(self, key: str) -> Approval | None:
        row = self.session.scalar(select(ApprovalRow).where(ApprovalRow.idempotency_key == key))
        return self._map(row) if row else None

    def list_for_user(self, user_id: str) -> list[Approval]:
        rows = self.session.scalars(
            select(ApprovalRow)
            .where(ApprovalRow.user_id == user_id)
            .order_by(desc(ApprovalRow.created_at))
        )
        return [self._map(row) for row in rows]

    @staticmethod
    def _map(row: ApprovalRow) -> Approval:
        return Approval(
            id=row.id,
            user_id=row.user_id,
            requester_id=row.requester_id,
            approver_id=row.approver_id,
            proposal_id=row.proposal_id,
            permission=row.permission,
            action_level=row.action_level,
            environment=row.environment,
            target_type=row.target_type,
            target_id=row.target_id,
            input_snapshot_hash=row.input_snapshot_hash,
            calendar_provider_id=row.calendar_provider_id,
            calendar_snapshot_version=row.calendar_snapshot_version,
            provider_id=row.provider_id,
            on_behalf_of_id=row.on_behalf_of_id,
            disclosed_data=row.disclosed_data,
            audience=row.audience,
            reversible=row.reversible,
            expected_consequence=row.expected_consequence,
            status=ApprovalStatus(row.status),
            action_digest=row.action_digest,
            proposal_version=row.proposal_version,
            commitment_version=row.commitment_version,
            policy_version=row.policy_version,
            expires_at=aware(row.expires_at),  # type: ignore[arg-type]
            nonce=row.nonce,
            idempotency_key=row.idempotency_key,
            created_at=aware(row.created_at),  # type: ignore[arg-type]
            consumed_at=aware(row.consumed_at),
        )


class SqlWorldFactRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def add(self, entity: WorldFact) -> None:
        self.session.merge(
            WorldFactRow(
                id=entity.id,
                user_id=entity.user_id,
                fact_type=entity.fact_type,
                label=entity.label,
                occurs_at=entity.occurs_at,
                provenance_json=provenance_json(entity.provenance),
                created_at=entity.created_at,
            )
        )

    def find_confirmed_by_label(self, user_id: str, label: str) -> WorldFact | None:
        rows = self.session.scalars(
            select(WorldFactRow).where(
                WorldFactRow.user_id == user_id,
                WorldFactRow.label == label,
            )
        )
        for row in rows:
            fact = self._map(row)
            if fact.provenance.confirmation_status is ConfirmationStatus.CONFIRMED:
                return fact
        return None

    @staticmethod
    def _map(row: WorldFactRow) -> WorldFact:
        return WorldFact(
            id=row.id,
            user_id=row.user_id,
            fact_type=row.fact_type,
            label=row.label,
            occurs_at=aware(row.occurs_at),  # type: ignore[arg-type]
            provenance=parse_provenance(row.provenance_json),
            created_at=aware(row.created_at),  # type: ignore[arg-type]
        )


class SqlProjectRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def add(self, entity: Project) -> None:
        self.session.merge(
            ProjectRow(
                id=entity.id,
                user_id=entity.user_id,
                name=entity.name,
                status=entity.status,
                is_primary=entity.is_primary,
                created_at=entity.created_at,
            )
        )

    def primary_for_user(self, user_id: str) -> Project | None:
        row = self.session.scalar(
            select(ProjectRow).where(ProjectRow.user_id == user_id, ProjectRow.is_primary.is_(True))
        )
        return self._map(row) if row else None

    def list_for_user(self, user_id: str) -> list[Project]:
        rows = self.session.scalars(select(ProjectRow).where(ProjectRow.user_id == user_id))
        return [self._map(row) for row in rows]

    @staticmethod
    def _map(row: ProjectRow) -> Project:
        return Project(
            id=row.id,
            user_id=row.user_id,
            name=row.name,
            status=row.status,
            is_primary=row.is_primary,
            created_at=aware(row.created_at),  # type: ignore[arg-type]
        )


class SqlTransactionRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def add(self, entity: FinancialTransaction) -> None:
        self.session.merge(
            FinancialTransactionRow(
                id=entity.id,
                user_id=entity.user_id,
                household_id=entity.household_id,
                project_id=entity.project_id,
                merchant=entity.merchant,
                memo=entity.memo,
                amount_minor=entity.amount_minor,
                currency=entity.currency,
                posted_at=entity.posted_at,
                provenance_json=provenance_json(entity.provenance),
                created_at=entity.created_at,
            )
        )

    def get(self, entity_id: str) -> FinancialTransaction | None:
        row = self.session.get(FinancialTransactionRow, entity_id)
        return self._map(row) if row else None

    def list_for_user(self, user_id: str) -> list[FinancialTransaction]:
        rows = self.session.scalars(
            select(FinancialTransactionRow)
            .where(FinancialTransactionRow.user_id == user_id)
            .order_by(desc(FinancialTransactionRow.posted_at))
        )
        return [self._map(row) for row in rows]

    @staticmethod
    def _map(row: FinancialTransactionRow) -> FinancialTransaction:
        return FinancialTransaction(
            id=row.id,
            user_id=row.user_id,
            household_id=row.household_id,
            project_id=row.project_id,
            merchant=row.merchant,
            memo=row.memo,
            amount_minor=row.amount_minor,
            currency=row.currency,
            posted_at=aware(row.posted_at),  # type: ignore[arg-type]
            provenance=parse_provenance(row.provenance_json),
            created_at=aware(row.created_at),  # type: ignore[arg-type]
        )


class SqlClassificationRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def add(self, entity: TransactionClassification) -> None:
        self.session.merge(
            TransactionClassificationRow(
                id=entity.id,
                transaction_id=entity.transaction_id,
                category=entity.category,
                rule_id=entity.rule_id,
                confidence=round(entity.confidence * 10000),
                status=entity.status.value,
                provenance_json=provenance_json(entity.provenance),
                created_at=entity.created_at,
            )
        )

    def latest_for_transaction(self, transaction_id: str) -> TransactionClassification | None:
        row = self.session.scalar(
            select(TransactionClassificationRow)
            .where(TransactionClassificationRow.transaction_id == transaction_id)
            .order_by(desc(TransactionClassificationRow.created_at))
            .limit(1)
        )
        return self._map(row) if row else None

    @staticmethod
    def _map(row: TransactionClassificationRow) -> TransactionClassification:
        return TransactionClassification(
            id=row.id,
            transaction_id=row.transaction_id,
            category=row.category,
            rule_id=row.rule_id,
            confidence=row.confidence / 10000,
            status=ClassificationStatus(row.status),
            provenance=parse_provenance(row.provenance_json),
            created_at=aware(row.created_at),  # type: ignore[arg-type]
        )


class SqlAuditRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def append(self, entity: AuditEvent) -> None:
        self.session.add(
            AuditEventRow(
                id=entity.id,
                user_id=entity.user_id,
                action=entity.action,
                entity_type=entity.entity_type,
                entity_id=entity.entity_id,
                correlation_id=entity.correlation_id,
                occurred_at=entity.occurred_at,
                outcome=entity.outcome,
                source_type=entity.source_type,
                source_identifier=entity.source_identifier,
                actor_id=entity.actor_id,
                on_behalf_of_id=entity.on_behalf_of_id,
                entity_version=entity.entity_version,
                causation_id=entity.causation_id,
                policy_result=entity.policy_result,
                capability_mode=entity.capability_mode,
                approval_id=entity.approval_id,
                tool_reference=entity.tool_reference,
                agent_reference=entity.agent_reference,
                summary=entity.summary,
                details_json=json.dumps(entity.details, sort_keys=True),
            )
        )

    def list_for_user(self, user_id: str, limit: int = 100) -> list[AuditEvent]:
        rows = self.session.scalars(
            select(AuditEventRow)
            .where(AuditEventRow.user_id == user_id)
            .order_by(desc(AuditEventRow.occurred_at))
            .limit(limit)
        )
        return [
            AuditEvent(
                id=row.id,
                user_id=row.user_id,
                action=row.action,
                entity_type=row.entity_type,
                entity_id=row.entity_id,
                correlation_id=row.correlation_id,
                occurred_at=aware(row.occurred_at),  # type: ignore[arg-type]
                outcome=row.outcome,
                source_type=row.source_type,
                source_identifier=row.source_identifier,
                actor_id=row.actor_id,
                on_behalf_of_id=row.on_behalf_of_id,
                entity_version=row.entity_version,
                causation_id=row.causation_id,
                policy_result=row.policy_result,
                capability_mode=row.capability_mode,
                approval_id=row.approval_id,
                tool_reference=row.tool_reference,
                agent_reference=row.agent_reference,
                summary=row.summary,
                details=json.loads(row.details_json),
            )
            for row in rows
        ]


class SqlOutboxRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def enqueue(self, event: OutboxEvent) -> None:
        # SQLite's CURRENT_TIMESTAMP has second precision. Normalizing only the
        # eligibility timestamp keeps an immediately available local event claimable while
        # retaining the full authoritative occurrence timestamp.
        available_at = (event.available_at or event.occurred_at).replace(microsecond=0)
        self.session.add(
            OutboxEventRow(
                id=event.id,
                event_type=event.event_type.value,
                schema_version=event.schema_version,
                aggregate_type=event.aggregate_type,
                aggregate_id=event.aggregate_id,
                aggregate_version=event.aggregate_version,
                owner_user_id=event.owner_user_id,
                controller_id=event.controller_id,
                data_subject_id=event.data_subject_id,
                actor_id=event.actor_id,
                on_behalf_of_id=event.on_behalf_of_id,
                sensitivity=event.sensitivity,
                correlation_id=event.correlation_id,
                causation_id=event.causation_id,
                occurred_at=event.occurred_at,
                capability_mode=event.capability_mode,
                producer_key=event.producer_key,
                payload_json=json.dumps(event.payload, sort_keys=True, separators=(",", ":")),
                status=event.status.value,
                available_at=available_at,
                attempt_count=event.attempt_count,
                max_attempts=event.max_attempts,
                cycle=event.cycle,
                lease_owner=event.lease_owner,
                lease_token=event.lease_token,
                lease_expires_at=event.lease_expires_at,
                last_failure_code=event.last_failure_code,
                created_at=event.occurred_at,
                delivered_at=event.delivered_at,
            )
        )

    def get(self, event_id: str) -> OutboxEvent | None:
        row = self.session.get(OutboxEventRow, event_id)
        return self._map(row) if row else None

    def claim_next(self, worker_id: str, lease_seconds: int) -> OutboxEvent | None:
        if not worker_id.strip() or not 1 <= lease_seconds <= 300:
            raise ValueError("worker identity and a 1-300 second lease are required")
        now = self._database_now()
        statement = (
            select(OutboxEventRow)
            .where(
                or_(
                    and_(
                        OutboxEventRow.status.in_(
                            (OutboxStatus.PENDING.value, OutboxStatus.RETRY.value)
                        ),
                        OutboxEventRow.available_at <= now,
                    ),
                    and_(
                        OutboxEventRow.status == OutboxStatus.PROCESSING.value,
                        OutboxEventRow.lease_expires_at <= now,
                    ),
                )
            )
            .order_by(OutboxEventRow.available_at, OutboxEventRow.occurred_at, OutboxEventRow.id)
            .limit(1)
        )
        if self.session.get_bind().dialect.name == "postgresql":
            statement = statement.with_for_update(skip_locked=True)
        row = self.session.scalar(statement)
        if row is None:
            return None
        was_expired = row.status == OutboxStatus.PROCESSING.value
        if was_expired and row.attempt_count >= row.max_attempts:
            row.status = OutboxStatus.FAILED.value
            row.lease_owner = None
            row.lease_token = None
            row.lease_expires_at = None
            row.last_failure_code = "lease-expired-attempt-budget"
            self._append_transition(
                row,
                OutboxTransitionType.FAILED,
                now,
                worker_id=worker_id,
                failure_code=row.last_failure_code,
                policy_result="denied:attempt-budget-exhausted",
            )
            self.session.flush()
            return self._map(row)
        row.status = OutboxStatus.PROCESSING.value
        row.attempt_count += 1
        row.lease_owner = worker_id
        row.lease_token = uuid4().hex
        row.lease_expires_at = now + timedelta(seconds=lease_seconds)
        row.last_failure_code = None
        self._append_transition(
            row,
            (OutboxTransitionType.RECLAIMED if was_expired else OutboxTransitionType.CLAIMED),
            now,
            worker_id=worker_id,
            lease_token=row.lease_token,
            policy_result="preauthorization:execution-claim-v1",
        )
        self.session.flush()
        return self._map(row)

    def mark_delivered(
        self,
        event_id: str,
        worker_id: str,
        lease_token: str,
        *,
        duplicate_suppressed: bool = False,
    ) -> OutboxEvent:
        from personal_os.domain.errors import ConflictError

        row = self.session.get(OutboxEventRow, event_id)
        if row is None:
            raise ConflictError("outbox event is unavailable")
        is_postgresql = self.session.get_bind().dialect.name == "postgresql"
        database_time = func.clock_timestamp() if is_postgresql else self._database_now()
        statement = (
            update(OutboxEventRow)
            .where(
                OutboxEventRow.id == event_id,
                OutboxEventRow.status == OutboxStatus.PROCESSING.value,
                OutboxEventRow.lease_owner == worker_id,
                OutboxEventRow.lease_token == lease_token,
                OutboxEventRow.lease_expires_at > database_time,
            )
            .values(
                status=OutboxStatus.DELIVERED.value,
                lease_owner=None,
                lease_token=None,
                lease_expires_at=None,
                last_failure_code=None,
                delivered_at=database_time,
            )
            .execution_options(synchronize_session=False)
        )
        if is_postgresql:
            delivered_at = self.session.scalar(statement.returning(OutboxEventRow.delivered_at))
            if delivered_at is None:
                raise ConflictError("outbox lease is stale or no longer owned")
            transition_time = aware(delivered_at)
            if transition_time is None:  # pragma: no cover - non-null returning column
                raise RuntimeError("database delivery timestamp is missing")
        else:
            result = self.session.execute(statement)
            if getattr(result, "rowcount", 0) != 1:
                raise ConflictError("outbox lease is stale or no longer owned")
            if not isinstance(database_time, datetime):  # pragma: no cover - SQLite branch
                raise RuntimeError("database delivery timestamp is missing")
            transition_time = database_time
        self._append_transition(
            row,
            (
                OutboxTransitionType.DUPLICATE_SUPPRESSED
                if duplicate_suppressed
                else OutboxTransitionType.DELIVERED
            ),
            transition_time,
            worker_id=worker_id,
            lease_token=lease_token,
            policy_result="allowed:execution-delivery-v1",
        )
        self.session.expire(row)
        self.session.flush()
        refreshed = self.session.get(OutboxEventRow, event_id)
        if refreshed is None:  # pragma: no cover - protected by the update predicate
            raise ConflictError("delivered outbox event disappeared")
        return self._map(refreshed)

    def record_failure(
        self,
        event_id: str,
        worker_id: str,
        lease_token: str,
        failure_code: str,
        *,
        retryable: bool,
        policy_result: str,
    ) -> OutboxEvent:
        from personal_os.domain.errors import ConflictError
        from personal_os.domain.events import FAILURE_CODE_PATTERN

        if not FAILURE_CODE_PATTERN.fullmatch(failure_code):
            raise ValueError("failure code must be a typed redacted code")
        row = self.session.get(OutboxEventRow, event_id)
        if row is None:
            raise ConflictError("outbox event is unavailable")
        is_postgresql = self.session.get_bind().dialect.name == "postgresql"
        database_time = func.clock_timestamp() if is_postgresql else self._database_now()
        should_retry = retryable and row.attempt_count < row.max_attempts
        target = OutboxStatus.RETRY if should_retry else OutboxStatus.FAILED
        backoff_seconds = min(60, 2 ** max(0, row.attempt_count - 1))
        values: dict[str, object] = {
            "status": target.value,
            "lease_owner": None,
            "lease_token": None,
            "lease_expires_at": None,
            "last_failure_code": failure_code,
            "delivered_at": None,
        }
        if should_retry:
            values["available_at"] = database_time + timedelta(seconds=backoff_seconds)
        elif is_postgresql:
            # Persist the wall-clock transition instant so RETURNING can supply the exact
            # timestamp from the same fenced statement even for terminal failure.
            values["available_at"] = database_time
        statement = (
            update(OutboxEventRow)
            .where(
                OutboxEventRow.id == event_id,
                OutboxEventRow.status == OutboxStatus.PROCESSING.value,
                OutboxEventRow.lease_owner == worker_id,
                OutboxEventRow.lease_token == lease_token,
                OutboxEventRow.lease_expires_at > database_time,
            )
            .values(**values)
            .execution_options(synchronize_session=False)
        )
        if is_postgresql:
            available_at = self.session.scalar(statement.returning(OutboxEventRow.available_at))
            if available_at is None:
                raise ConflictError("outbox lease is stale or no longer owned")
            transition_time = aware(available_at)
            if transition_time is None:  # pragma: no cover - non-null returning column
                raise RuntimeError("database failure timestamp is missing")
            if should_retry:
                transition_time -= timedelta(seconds=backoff_seconds)
        else:
            result = self.session.execute(statement)
            if getattr(result, "rowcount", 0) != 1:
                raise ConflictError("outbox lease is stale or no longer owned")
            if not isinstance(database_time, datetime):  # pragma: no cover - SQLite branch
                raise RuntimeError("database failure timestamp is missing")
            transition_time = database_time
        self._append_transition(
            row,
            (OutboxTransitionType.RETRY_SCHEDULED if should_retry else OutboxTransitionType.FAILED),
            transition_time,
            worker_id=worker_id,
            lease_token=lease_token,
            failure_code=failure_code,
            policy_result=policy_result,
        )
        self.session.expire(row)
        self.session.flush()
        refreshed = self.session.get(OutboxEventRow, event_id)
        if refreshed is None:  # pragma: no cover - protected by the update predicate
            raise ConflictError("failed outbox event disappeared")
        return self._map(refreshed)

    def recover(
        self,
        event_id: str,
        actor_id: str,
        reason: str,
        policy_result: str,
    ) -> OutboxEvent:
        from personal_os.domain.errors import ConflictError

        if not actor_id.strip() or not 1 <= len(reason.strip()) <= 240:
            raise ValueError("recovery requires an actor and a 1-240 character reason")
        statement = select(OutboxEventRow).where(OutboxEventRow.id == event_id)
        if self.session.get_bind().dialect.name == "postgresql":
            row = _run_with_scoped_postgresql_lock_timeout(
                self.session,
                lambda: self.session.scalar(statement.with_for_update()),
            )
        else:
            row = self.session.scalar(statement)
        if row is None or row.status != OutboxStatus.FAILED.value:
            raise ConflictError("only failed outbox work can be recovered")
        now = self._database_now()
        row.status = OutboxStatus.PENDING.value
        row.available_at = now
        row.attempt_count = 0
        row.cycle += 1
        row.lease_owner = None
        row.lease_token = None
        row.lease_expires_at = None
        row.last_failure_code = None
        row.delivered_at = None
        self._append_transition(
            row,
            OutboxTransitionType.RECOVERED,
            now,
            actor_id=actor_id,
            policy_result=policy_result,
            reason=reason.strip(),
        )
        self.session.flush()
        return self._map(row)

    def list_failed(self, owner_user_id: str) -> list[OutboxEvent]:
        rows = self.session.scalars(
            select(OutboxEventRow)
            .where(
                OutboxEventRow.owner_user_id == owner_user_id,
                OutboxEventRow.status == OutboxStatus.FAILED.value,
            )
            .order_by(OutboxEventRow.occurred_at)
        )
        return [self._map(row) for row in rows]

    def status_counts(self, owner_user_id: str) -> dict[OutboxStatus, int]:
        result = {status: 0 for status in OutboxStatus}
        rows = self.session.execute(
            select(OutboxEventRow.status, func.count(OutboxEventRow.id))
            .where(OutboxEventRow.owner_user_id == owner_user_id)
            .group_by(OutboxEventRow.status)
        )
        for status, count in rows:
            result[OutboxStatus(status)] = int(count)
        return result

    def _database_now(self) -> datetime:
        clock = (
            func.clock_timestamp()
            if self.session.get_bind().dialect.name == "postgresql"
            else func.current_timestamp()
        )
        value = self.session.scalar(select(clock))
        if not isinstance(value, datetime):
            raise RuntimeError("database did not return a current timestamp")
        result = aware(value)
        if result is None:  # pragma: no cover - guarded by isinstance
            raise RuntimeError("database timestamp is missing")
        return result

    def _append_transition(
        self,
        row: OutboxEventRow,
        transition: OutboxTransitionType,
        occurred_at: datetime,
        *,
        worker_id: str | None = None,
        lease_token: str | None = None,
        actor_id: str | None = None,
        failure_code: str | None = None,
        policy_result: str | None = None,
        reason: str | None = None,
    ) -> None:
        current = self.session.scalar(
            select(func.coalesce(func.max(OutboxTransitionRow.sequence), 0)).where(
                OutboxTransitionRow.event_id == row.id
            )
        )
        sequence = int(current or 0) + 1
        self.session.add(
            OutboxTransitionRow(
                id=f"outbox-transition-{uuid4().hex}",
                event_id=row.id,
                sequence=sequence,
                cycle=row.cycle,
                attempt_number=row.attempt_count,
                transition=transition.value,
                occurred_at=occurred_at,
                worker_id=worker_id,
                lease_token=lease_token,
                actor_id=actor_id,
                failure_code=failure_code,
                policy_result=policy_result,
                reason=reason,
            )
        )

    @staticmethod
    def _map(row: OutboxEventRow) -> OutboxEvent:
        return OutboxEvent(
            id=row.id,
            event_type=InternalEventType(row.event_type),
            schema_version=row.schema_version,
            aggregate_type=row.aggregate_type,
            aggregate_id=row.aggregate_id,
            aggregate_version=row.aggregate_version,
            owner_user_id=row.owner_user_id,
            controller_id=row.controller_id,
            data_subject_id=row.data_subject_id,
            actor_id=row.actor_id,
            on_behalf_of_id=row.on_behalf_of_id,
            sensitivity=row.sensitivity,
            correlation_id=row.correlation_id,
            causation_id=row.causation_id,
            occurred_at=aware(row.occurred_at),  # type: ignore[arg-type]
            capability_mode=row.capability_mode,
            producer_key=row.producer_key,
            payload=json.loads(row.payload_json),
            status=OutboxStatus(row.status),
            available_at=aware(row.available_at),
            attempt_count=row.attempt_count,
            max_attempts=row.max_attempts,
            cycle=row.cycle,
            lease_owner=row.lease_owner,
            lease_token=row.lease_token,
            lease_expires_at=aware(row.lease_expires_at),
            last_failure_code=row.last_failure_code,
            delivered_at=aware(row.delivered_at),
        )


class SqlConsumerReceiptRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def add(self, receipt: ConsumerReceipt) -> None:
        # The receipt has a database FK to the effect built immediately before it.
        # Flush the effect inside the same transaction so PostgreSQL never observes the
        # dependent receipt first; a later fencing conflict still rolls both rows back.
        self.session.flush()
        self.session.add(
            ConsumerReceiptRow(
                consumer_name=receipt.consumer_name,
                event_id=receipt.event_id,
                effect_id=receipt.effect_id,
                processed_at=receipt.processed_at,
            )
        )

    def get(self, consumer_name: str, event_id: str) -> ConsumerReceipt | None:
        row = self.session.get(ConsumerReceiptRow, (consumer_name, event_id))
        if row is None:
            return None
        return ConsumerReceipt(
            consumer_name=row.consumer_name,
            event_id=row.event_id,
            effect_id=row.effect_id,
            processed_at=aware(row.processed_at),  # type: ignore[arg-type]
        )


class SqlInternalEffectRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def add(self, effect: InternalEffect) -> None:
        self.session.add(
            InternalEffectRow(
                id=effect.id,
                consumer_name=effect.consumer_name,
                event_id=effect.event_id,
                owner_user_id=effect.owner_user_id,
                effect_type=effect.effect_type,
                occurred_at=effect.occurred_at,
                payload_json=json.dumps(effect.payload, sort_keys=True, separators=(",", ":")),
            )
        )

    def get_for_event(self, consumer_name: str, event_id: str) -> InternalEffect | None:
        row = self.session.scalar(
            select(InternalEffectRow).where(
                InternalEffectRow.consumer_name == consumer_name,
                InternalEffectRow.event_id == event_id,
            )
        )
        if row is None:
            return None
        return InternalEffect(
            id=row.id,
            consumer_name=row.consumer_name,
            event_id=row.event_id,
            owner_user_id=row.owner_user_id,
            effect_type=row.effect_type,
            occurred_at=aware(row.occurred_at),  # type: ignore[arg-type]
            payload=json.loads(row.payload_json),
        )


class SqlOutboxTransitionRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def list_for_event(self, event_id: str) -> list[OutboxTransition]:
        rows = self.session.scalars(
            select(OutboxTransitionRow)
            .where(OutboxTransitionRow.event_id == event_id)
            .order_by(OutboxTransitionRow.sequence)
        )
        return [
            OutboxTransition(
                id=row.id,
                event_id=row.event_id,
                sequence=row.sequence,
                cycle=row.cycle,
                attempt_number=row.attempt_number,
                transition=OutboxTransitionType(row.transition),
                occurred_at=aware(row.occurred_at),  # type: ignore[arg-type]
                worker_id=row.worker_id,
                lease_token=row.lease_token,
                actor_id=row.actor_id,
                failure_code=row.failure_code,
                policy_result=row.policy_result,
                reason=row.reason,
            )
            for row in rows
        ]


class SqlUnitOfWork(UnitOfWork):
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

    def __init__(self, session_factory: Callable[[], Session]) -> None:
        self.session_factory = session_factory
        self.session: Session | None = None
        self._committed = False

    def __enter__(self) -> UnitOfWork:
        self.session = self.session_factory()
        self.intents = SqlIntentRepository(self.session)
        self.commitments = SqlCommitmentRepository(self.session)
        self.proposals = SqlProposalRepository(self.session)
        self.blocks = SqlBlockRepository(self.session)
        self.approvals = SqlApprovalRepository(self.session)
        self.receipts = SqlCommandReceiptRepository(self.session)
        self.world_facts = SqlWorldFactRepository(self.session)
        self.projects = SqlProjectRepository(self.session)
        self.transactions = SqlTransactionRepository(self.session)
        self.classifications = SqlClassificationRepository(self.session)
        self.audit = SqlAuditRepository(self.session)
        self.outbox = SqlOutboxRepository(self.session)
        self.consumer_receipts = SqlConsumerReceiptRepository(self.session)
        self.internal_effects = SqlInternalEffectRepository(self.session)
        self.outbox_transitions = SqlOutboxTransitionRepository(self.session)
        return self

    def __exit__(self, *args: object) -> None:
        if self.session is None:
            return
        integrity_error = args[1] if len(args) > 1 and isinstance(args[1], IntegrityError) else None
        if args[0] is not None or not self._committed:
            self.session.rollback()
        self.session.close()
        if integrity_error is not None:
            from personal_os.domain.errors import ConflictError

            raise ConflictError("a concurrent or duplicate write was rejected") from integrity_error

    def commit(self) -> None:
        if self.session is None:
            raise RuntimeError("unit of work has not started")
        try:
            self.session.commit()
        except IntegrityError as exc:
            self.session.rollback()
            from personal_os.domain.errors import ConflictError

            raise ConflictError("a concurrent or duplicate write was rejected") from exc
        self._committed = True

    def rollback(self) -> None:
        if self.session is not None:
            self.session.rollback()


def create_uow_factory(engine: Engine) -> Callable[[], UnitOfWork]:
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    return lambda: SqlUnitOfWork(factory)
