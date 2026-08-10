from __future__ import annotations

import json
from collections.abc import Callable
from datetime import UTC, datetime

from sqlalchemy import Engine, desc, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker

from personal_os.adapters.persistence.models import (
    ApprovalRow,
    AuditEventRow,
    CommandReceiptRow,
    CommitmentRow,
    FinancialTransactionRow,
    IntentRow,
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
from personal_os.domain.provenance import ConfirmationStatus, Provenance
from personal_os.ports.repositories import (
    ApprovalRepository,
    AuditRepository,
    BlockRepository,
    ClassificationRepository,
    CommandReceiptRepository,
    CommitmentRepository,
    IntentRepository,
    ProjectRepository,
    ProposalRepository,
    TransactionRepository,
    UnitOfWork,
    WorldFactRepository,
)


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
        return self

    def __exit__(self, *args: object) -> None:
        if self.session is None:
            return
        if args[0] is not None or not self._committed:
            self.session.rollback()
        self.session.close()

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
