from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class IntentRow(Base):
    __tablename__ = "intents"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    user_id: Mapped[str] = mapped_column(String(64), index=True)
    raw_text: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(32), index=True)
    provenance_json: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    title: Mapped[str | None] = mapped_column(String(240), nullable=True)
    due_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    duration_minutes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    clarification_question: Mapped[str | None] = mapped_column(Text, nullable=True)
    commitment_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    version: Mapped[int] = mapped_column(Integer, default=1)


class CommitmentRow(Base):
    __tablename__ = "commitments"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    user_id: Mapped[str] = mapped_column(String(64), index=True)
    title: Mapped[str] = mapped_column(String(240))
    status: Mapped[str] = mapped_column(String(32), index=True)
    due_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    duration_minutes: Mapped[int] = mapped_column(Integer)
    provenance_json: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    schedule_block_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    waiting_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    review_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    abandoned_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    version: Mapped[int] = mapped_column(Integer, default=1)


class ScheduleProposalRow(Base):
    __tablename__ = "schedule_proposals"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    user_id: Mapped[str] = mapped_column(String(64), index=True)
    commitment_id: Mapped[str] = mapped_column(String(64), ForeignKey("commitments.id"), index=True)
    starts_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    ends_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    status: Mapped[str] = mapped_column(String(32), index=True)
    rationale: Mapped[str] = mapped_column(Text)
    input_snapshot_hash: Mapped[str] = mapped_column(String(64))
    revision: Mapped[int] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    provenance_json: Mapped[str] = mapped_column(Text)
    calendar_provider_id: Mapped[str] = mapped_column(String(120))
    calendar_snapshot_version: Mapped[str] = mapped_column(String(120))
    supersedes_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    version: Mapped[int] = mapped_column(Integer, default=1)


class ScheduleBlockRow(Base):
    __tablename__ = "schedule_blocks"
    __table_args__ = (
        UniqueConstraint("commitment_id", name="uq_schedule_block_commitment"),
        UniqueConstraint(
            "user_id", "starts_at", "ends_at", name="uq_schedule_block_exact_interval"
        ),
        Index("ix_schedule_block_user_interval", "user_id", "starts_at", "ends_at"),
    )

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    user_id: Mapped[str] = mapped_column(String(64), index=True)
    commitment_id: Mapped[str] = mapped_column(String(64), ForeignKey("commitments.id"), index=True)
    starts_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    ends_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    status: Mapped[str] = mapped_column(String(32), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class ApprovalRow(Base):
    __tablename__ = "approvals"
    __table_args__ = (UniqueConstraint("idempotency_key", name="uq_approval_idempotency"),)

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    user_id: Mapped[str] = mapped_column(String(64), index=True)
    requester_id: Mapped[str] = mapped_column(String(64))
    approver_id: Mapped[str] = mapped_column(String(64))
    proposal_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("schedule_proposals.id"), index=True
    )
    permission: Mapped[str] = mapped_column(String(120))
    action_level: Mapped[int] = mapped_column(Integer)
    environment: Mapped[str] = mapped_column(String(64))
    target_type: Mapped[str] = mapped_column(String(80))
    target_id: Mapped[str] = mapped_column(String(64))
    input_snapshot_hash: Mapped[str] = mapped_column(String(64))
    calendar_provider_id: Mapped[str] = mapped_column(String(120))
    calendar_snapshot_version: Mapped[str] = mapped_column(String(120))
    provider_id: Mapped[str] = mapped_column(String(120))
    on_behalf_of_id: Mapped[str] = mapped_column(String(64))
    disclosed_data: Mapped[str] = mapped_column(Text)
    audience: Mapped[str] = mapped_column(String(160))
    reversible: Mapped[bool] = mapped_column(Boolean)
    expected_consequence: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(32), index=True)
    action_digest: Mapped[str] = mapped_column(String(64))
    proposal_version: Mapped[int] = mapped_column(Integer)
    commitment_version: Mapped[int] = mapped_column(Integer)
    policy_version: Mapped[str] = mapped_column(String(64))
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    nonce: Mapped[str] = mapped_column(String(64), unique=True)
    idempotency_key: Mapped[str] = mapped_column(String(128))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    consumed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class WorldFactRow(Base):
    __tablename__ = "world_facts"
    __table_args__ = (Index("ix_world_fact_user_label", "user_id", "label"),)

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    user_id: Mapped[str] = mapped_column(String(64))
    fact_type: Mapped[str] = mapped_column(String(64))
    label: Mapped[str] = mapped_column(String(160))
    occurs_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    provenance_json: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class ProjectRow(Base):
    __tablename__ = "projects"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    user_id: Mapped[str] = mapped_column(String(64), index=True)
    name: Mapped[str] = mapped_column(String(240))
    status: Mapped[str] = mapped_column(String(32))
    is_primary: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class FinancialTransactionRow(Base):
    __tablename__ = "financial_transactions"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    user_id: Mapped[str] = mapped_column(String(64), index=True)
    household_id: Mapped[str] = mapped_column(String(64), index=True)
    project_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    merchant: Mapped[str] = mapped_column(String(240))
    memo: Mapped[str] = mapped_column(Text)
    amount_minor: Mapped[int] = mapped_column(Integer)
    currency: Mapped[str] = mapped_column(String(3))
    posted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    provenance_json: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class TransactionClassificationRow(Base):
    __tablename__ = "transaction_classifications"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    transaction_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("financial_transactions.id"), index=True
    )
    category: Mapped[str] = mapped_column(String(160))
    rule_id: Mapped[str] = mapped_column(String(120))
    confidence: Mapped[int] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(32))
    provenance_json: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class AuditEventRow(Base):
    __tablename__ = "audit_events"
    __table_args__ = (Index("ix_audit_user_time", "user_id", "occurred_at"),)

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    user_id: Mapped[str] = mapped_column(String(64))
    action: Mapped[str] = mapped_column(String(120), index=True)
    entity_type: Mapped[str] = mapped_column(String(80))
    entity_id: Mapped[str] = mapped_column(String(64), index=True)
    correlation_id: Mapped[str] = mapped_column(String(64), index=True)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    outcome: Mapped[str] = mapped_column(String(32))
    source_type: Mapped[str] = mapped_column(String(32))
    source_identifier: Mapped[str] = mapped_column(String(240))
    actor_id: Mapped[str] = mapped_column(String(64), index=True)
    on_behalf_of_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    entity_version: Mapped[int] = mapped_column(Integer)
    causation_id: Mapped[str] = mapped_column(String(128), index=True)
    policy_result: Mapped[str] = mapped_column(String(160))
    capability_mode: Mapped[str] = mapped_column(String(64))
    approval_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    tool_reference: Mapped[str | None] = mapped_column(String(240), nullable=True)
    agent_reference: Mapped[str | None] = mapped_column(String(240), nullable=True)
    summary: Mapped[str] = mapped_column(Text)
    details_json: Mapped[str] = mapped_column(Text, default="{}")


class CommandReceiptRow(Base):
    __tablename__ = "command_receipts"

    idempotency_key: Mapped[str] = mapped_column(String(128), primary_key=True)
    user_id: Mapped[str] = mapped_column(String(64), index=True)
    command_type: Mapped[str] = mapped_column(String(80))
    request_digest: Mapped[str] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    intent_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    commitment_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    proposal_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    replacement_proposal_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
