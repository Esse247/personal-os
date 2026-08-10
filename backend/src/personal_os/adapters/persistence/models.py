from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
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
    __table_args__ = (
        CheckConstraint(
            "(outbox_event_id IS NULL AND result_json IS NULL) OR "
            "(outbox_event_id IS NOT NULL AND result_json IS NOT NULL)",
            name="ck_command_receipt_outbox_result_pair",
        ),
        CheckConstraint(
            "result_json IS NULL OR length(result_json) <= 2048",
            name="ck_command_receipt_result_size",
        ),
    )

    idempotency_key: Mapped[str] = mapped_column(String(128), primary_key=True)
    user_id: Mapped[str] = mapped_column(String(64), index=True)
    command_type: Mapped[str] = mapped_column(String(80))
    request_digest: Mapped[str] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    intent_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    commitment_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    proposal_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    replacement_proposal_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    outbox_event_id: Mapped[str | None] = mapped_column(
        String(64), ForeignKey("outbox_events.id"), nullable=True, index=True
    )
    result_json: Mapped[str | None] = mapped_column(Text, nullable=True)


class OutboxEventRow(Base):
    __tablename__ = "outbox_events"
    __table_args__ = (
        UniqueConstraint("producer_key", name="uq_outbox_event_producer_key"),
        CheckConstraint("schema_version = 1", name="ck_outbox_schema_version"),
        CheckConstraint("aggregate_version >= 0", name="ck_outbox_aggregate_version"),
        CheckConstraint(
            "sensitivity IN ('public', 'household_shared', 'personal', 'financial', "
            "'health', 'identity', 'legal')",
            name="ck_outbox_sensitivity",
        ),
        CheckConstraint(
            "capability_mode = 'local-mock-synthetic'",
            name="ck_outbox_capability_mode",
        ),
        CheckConstraint(
            "event_type IN ('intent.captured.v1', 'intent.clarification_requested.v1', "
            "'commitment.created.v1', 'schedule.no_feasible_proposal.v1', "
            "'schedule.proposed.v1', 'schedule.approved.v1', "
            "'schedule.rejected.v1', 'schedule.changed.v1', 'command.denied.v1')",
            name="ck_outbox_event_type",
        ),
        CheckConstraint(
            "status IN ('pending', 'processing', 'retry', 'delivered', 'failed')",
            name="ck_outbox_status",
        ),
        CheckConstraint(
            "attempt_count >= 0 AND attempt_count <= max_attempts "
            "AND max_attempts BETWEEN 1 AND 10",
            name="ck_outbox_attempt_budget",
        ),
        CheckConstraint("cycle >= 0", name="ck_outbox_cycle"),
        CheckConstraint("length(payload_json) <= 2048", name="ck_outbox_payload_size"),
        CheckConstraint(
            "(status = 'processing' AND lease_owner IS NOT NULL "
            "AND lease_token IS NOT NULL AND lease_expires_at IS NOT NULL) OR "
            "(status <> 'processing' AND lease_owner IS NULL "
            "AND lease_token IS NULL AND lease_expires_at IS NULL)",
            name="ck_outbox_lease_state",
        ),
        CheckConstraint(
            "(status IN ('retry', 'failed') AND last_failure_code IS NOT NULL) OR "
            "(status NOT IN ('retry', 'failed') AND last_failure_code IS NULL)",
            name="ck_outbox_failure_state",
        ),
        CheckConstraint(
            "(status = 'delivered' AND delivered_at IS NOT NULL) OR "
            "(status <> 'delivered' AND delivered_at IS NULL)",
            name="ck_outbox_delivery_state",
        ),
        Index("ix_outbox_eligible", "status", "available_at", "occurred_at"),
        Index("ix_outbox_owner_status", "owner_user_id", "status"),
    )

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    event_type: Mapped[str] = mapped_column(String(80), index=True)
    schema_version: Mapped[int] = mapped_column(Integer)
    aggregate_type: Mapped[str] = mapped_column(String(80))
    aggregate_id: Mapped[str] = mapped_column(String(64), index=True)
    aggregate_version: Mapped[int] = mapped_column(Integer)
    owner_user_id: Mapped[str] = mapped_column(String(64), index=True)
    controller_id: Mapped[str] = mapped_column(String(64))
    data_subject_id: Mapped[str] = mapped_column(String(64))
    actor_id: Mapped[str] = mapped_column(String(64))
    on_behalf_of_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    sensitivity: Mapped[str] = mapped_column(String(32))
    correlation_id: Mapped[str] = mapped_column(String(64), index=True)
    causation_id: Mapped[str] = mapped_column(String(128), index=True)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    capability_mode: Mapped[str] = mapped_column(String(64))
    producer_key: Mapped[str] = mapped_column(String(128))
    payload_json: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(32), index=True)
    available_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    attempt_count: Mapped[int] = mapped_column(Integer, default=0)
    max_attempts: Mapped[int] = mapped_column(Integer, default=3)
    cycle: Mapped[int] = mapped_column(Integer, default=0)
    lease_owner: Mapped[str | None] = mapped_column(String(64), nullable=True)
    lease_token: Mapped[str | None] = mapped_column(String(64), nullable=True)
    lease_expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    last_failure_code: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    delivered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class OutboxTransitionRow(Base):
    __tablename__ = "outbox_transitions"
    __table_args__ = (
        UniqueConstraint("event_id", "sequence", name="uq_outbox_transition_sequence"),
        CheckConstraint("sequence >= 1", name="ck_outbox_transition_sequence"),
        CheckConstraint("cycle >= 0", name="ck_outbox_transition_cycle"),
        CheckConstraint("attempt_number >= 0", name="ck_outbox_transition_attempt"),
        CheckConstraint(
            "transition IN ('claimed', 'reclaimed', 'retry_scheduled', "
            "'delivered', 'failed', 'recovered', 'duplicate_suppressed')",
            name="ck_outbox_transition_type",
        ),
        Index("ix_outbox_transition_event_time", "event_id", "occurred_at"),
    )

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    event_id: Mapped[str] = mapped_column(String(64), ForeignKey("outbox_events.id"), index=True)
    sequence: Mapped[int] = mapped_column(Integer)
    cycle: Mapped[int] = mapped_column(Integer)
    attempt_number: Mapped[int] = mapped_column(Integer)
    transition: Mapped[str] = mapped_column(String(32))
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    worker_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    lease_token: Mapped[str | None] = mapped_column(String(64), nullable=True)
    actor_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    failure_code: Mapped[str | None] = mapped_column(String(64), nullable=True)
    policy_result: Mapped[str | None] = mapped_column(String(160), nullable=True)
    reason: Mapped[str | None] = mapped_column(String(240), nullable=True)


class ConsumerReceiptRow(Base):
    __tablename__ = "consumer_receipts"
    __table_args__ = (
        UniqueConstraint("consumer_name", "event_id", name="uq_consumer_event_receipt"),
    )

    consumer_name: Mapped[str] = mapped_column(String(120), primary_key=True)
    event_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("outbox_events.id"), primary_key=True
    )
    effect_id: Mapped[str] = mapped_column(String(64), ForeignKey("internal_effects.id"))
    processed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class InternalEffectRow(Base):
    __tablename__ = "internal_effects"
    __table_args__ = (
        UniqueConstraint("consumer_name", "event_id", name="uq_internal_effect_consumer_event"),
    )

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    consumer_name: Mapped[str] = mapped_column(String(120))
    event_id: Mapped[str] = mapped_column(String(64), ForeignKey("outbox_events.id"), index=True)
    owner_user_id: Mapped[str] = mapped_column(String(64), index=True)
    effect_type: Mapped[str] = mapped_column(String(120))
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    payload_json: Mapped[str] = mapped_column(Text)
