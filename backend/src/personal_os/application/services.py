from __future__ import annotations

import json
from collections.abc import Callable, Mapping
from datetime import UTC, datetime, timedelta
from hashlib import sha256
from typing import Never
from uuid import uuid4

from personal_os.application.commands import (
    CaptureIntentCommand,
    CaptureIntentResult,
    DecideProposalCommand,
    DecideProposalResult,
    ProposalDecision,
)
from personal_os.application.policy import AuthContext, FoundationPolicy, ResourceRef
from personal_os.domain.entities import (
    Approval,
    ApprovalStatus,
    AuditEvent,
    BlockStatus,
    CommandReceipt,
    Commitment,
    CommitmentStatus,
    Intent,
    IntentStatus,
    ProposalStatus,
    ScheduleBlock,
    ScheduleProposal,
)
from personal_os.domain.errors import (
    AuthorizationError,
    ConflictError,
    InvalidTransitionError,
    NotFoundError,
    ValidationError,
)
from personal_os.domain.provenance import (
    ConfirmationStatus,
    Provenance,
    Sensitivity,
    SourceType,
)
from personal_os.domain.scheduling import (
    AvailabilitySlot,
    CalendarSnapshot,
    DeterministicScheduler,
    ScheduleRequest,
    intervals_overlap,
)
from personal_os.ports.providers import CalendarProvider, ModelProvider, ProviderRequestContext
from personal_os.ports.repositories import UnitOfWork

Clock = Callable[[], datetime]
IdFactory = Callable[[], str]
UnitOfWorkFactory = Callable[[], UnitOfWork]


def system_clock() -> datetime:
    return datetime.now(UTC)


def random_id() -> str:
    return str(uuid4())


class PersonalOSService:
    HAIRCUT_DURATION_MINUTES = 60  # Synthetic confirmed demo preference.
    BUFFER_MINUTES = 15
    CAPABILITY_MODE = "local-mock-synthetic"
    SYSTEM_ACTOR = "chief-of-staff-system"

    def __init__(
        self,
        *,
        uow_factory: UnitOfWorkFactory,
        model_provider: ModelProvider,
        calendar_provider: CalendarProvider,
        policy: FoundationPolicy | None = None,
        scheduler: DeterministicScheduler | None = None,
        clock: Clock = system_clock,
        id_factory: IdFactory = random_id,
    ) -> None:
        self.uow_factory = uow_factory
        self.model_provider = model_provider
        self.calendar_provider = calendar_provider
        self.policy = policy or FoundationPolicy()
        self.scheduler = scheduler or DeterministicScheduler()
        self.clock = clock
        self.id_factory = id_factory

    def capture_intent(self, command: CaptureIntentCommand) -> CaptureIntentResult:
        now = self.clock()
        context = AuthContext(command.user_id, "capture and plan user intention")
        request_digest = self._capture_request_digest(command)

        with self.uow_factory() as uow:
            self._authorize(
                uow,
                command,
                context,
                "intent.capture.own",
                ResourceRef("intent", "new", command.user_id, "personal"),
            )
            receipt = uow.receipts.get(command.idempotency_key)
            if receipt is not None:
                self._validate_receipt(
                    uow,
                    command,
                    receipt,
                    "capture_intent",
                    request_digest,
                )
                return self._replay_capture(uow, receipt)

            capture_provenance = Provenance(
                source_type=SourceType.USER_STATED,
                source_identifier=f"capture:{command.idempotency_key}",
                observed_at=now,
                recorded_at=now,
                confidence=1.0,
                confirmation_status=ConfirmationStatus.CONFIRMED,
                sensitivity=Sensitivity.PERSONAL,
                actor_id=command.user_id,
                data_subject_id=command.user_id,
                controller_id=command.user_id,
                correlation_id=command.correlation_id,
            )
            intent = Intent(
                id=self.id_factory(),
                user_id=command.user_id,
                raw_text=command.raw_text,
                status=IntentStatus.CAPTURED,
                provenance=capture_provenance,
                created_at=now,
            )
            uow.intents.add(intent)
            self._audit(
                uow,
                command,
                "intent.captured",
                "intent",
                intent.id,
                intent.version,
                "User statement captured as untrusted input.",
                SourceType.USER_STATED,
                capture_provenance.source_identifier,
            )

            model_context = self._provider_context(
                command,
                capability="model.intent.interpret",
                purpose="propose a schema-constrained interpretation",
                deadline_at=now + timedelta(seconds=30),
                task_type="intent_interpretation",
                risk="medium",
                privacy="personal",
            )
            self._authorize(
                uow,
                command,
                context,
                "provider.model.interpret.mock.own",
                ResourceRef(
                    "provider_capability",
                    model_context.capability,
                    command.user_id,
                    "personal",
                ),
            )
            interpretation = self.model_provider.interpret_intent(
                raw_text=command.raw_text,
                context=model_context,
            )
            if (
                interpretation.capability_mode != "mocked"
                or interpretation.observed_at is None
                or interpretation.provenance is None
                or interpretation.canonical_error is not None
            ):
                raise ValidationError("model provider returned an invalid Foundation envelope")

            if interpretation.missing_fields:
                intent.need_clarification(
                    interpretation.clarification_question
                    or "What details should I use to make this intention actionable?"
                )
                uow.intents.add(intent)
                self._audit(
                    uow,
                    command,
                    "intent.clarification_requested",
                    "intent",
                    intent.id,
                    intent.version,
                    "Missing facts were preserved instead of invented.",
                    SourceType.SYSTEM_INFERRED,
                    interpretation.provenance.source_identifier,
                    {"missing_fields": ",".join(interpretation.missing_fields)},
                )
                self._record_capture_receipt(uow, command, request_digest, intent, None, None, now)
                uow.commit()
                return CaptureIntentResult(intent, None, None)

            if not interpretation.title or not interpretation.related_fact_label:
                raise ValidationError("interpreter proposal is missing validated fields")
            fact = uow.world_facts.find_confirmed_by_label(
                command.user_id, interpretation.related_fact_label
            )
            if fact is None:
                intent.need_clarification(
                    f"What date is the {interpretation.related_fact_label.lower()}?"
                )
                uow.intents.add(intent)
                self._audit(
                    uow,
                    command,
                    "intent.clarification_requested",
                    "intent",
                    intent.id,
                    intent.version,
                    "The referenced deadline had no confirmed world fact.",
                    SourceType.SYSTEM_INFERRED,
                    interpretation.provenance.source_identifier,
                    {"missing_fact": interpretation.related_fact_label},
                )
                self._record_capture_receipt(uow, command, request_digest, intent, None, None, now)
                uow.commit()
                return CaptureIntentResult(intent, None, None)

            duration = interpretation.duration_minutes or self.HAIRCUT_DURATION_MINUTES
            intent.structure(
                title=interpretation.title, due_at=fact.occurs_at, duration_minutes=duration
            )
            commitment_provenance = Provenance(
                source_type=SourceType.SYSTEM_INFERRED,
                source_identifier=f"validated-command:{command.idempotency_key}",
                observed_at=now,
                recorded_at=now,
                confidence=min(
                    interpretation.provenance.confidence,
                    fact.provenance.confidence,
                ),
                confirmation_status=ConfirmationStatus.CONFIRMED,
                sensitivity=Sensitivity.PERSONAL,
                actor_id=self.SYSTEM_ACTOR,
                data_subject_id=command.user_id,
                controller_id=command.user_id,
                correlation_id=command.correlation_id,
                valid_until=fact.occurs_at,
                input_references=(
                    capture_provenance.source_identifier,
                    interpretation.provenance.source_identifier,
                    fact.provenance.source_identifier,
                    "synthetic-preference:haircut-duration-60m",
                ),
            )
            commitment = Commitment(
                id=self.id_factory(),
                user_id=command.user_id,
                title=interpretation.title,
                status=CommitmentStatus.CAPTURED,
                due_at=fact.occurs_at,
                duration_minutes=duration,
                provenance=commitment_provenance,
                created_at=now,
            )
            intent.commit(commitment.id)
            uow.intents.add(intent)
            uow.commitments.add(commitment)
            self._audit(
                uow,
                command,
                "commitment.created",
                "commitment",
                commitment.id,
                commitment.version,
                "Validated interpretation became an auditable commitment.",
                SourceType.SYSTEM_INFERRED,
                commitment_provenance.source_identifier,
                {
                    "deadline_source": fact.provenance.source_identifier,
                    "model_source": interpretation.provenance.source_identifier,
                },
            )

            calendar_context = self._provider_context(
                command,
                capability="calendar.availability.read.mock",
                purpose="find a feasible internal schedule proposal",
                deadline_at=fact.occurs_at,
                task_type="deterministic_scheduling",
                risk="medium",
                privacy="personal",
            )
            self._authorize(
                uow,
                command,
                context,
                "provider.calendar.availability.read.mock.own",
                ResourceRef(
                    "provider_capability",
                    calendar_context.capability,
                    command.user_id,
                    "personal",
                ),
            )
            snapshot = self.calendar_provider.availability(
                user_id=command.user_id,
                before_iso=fact.occurs_at.isoformat(),
                context=calendar_context,
            )
            if snapshot.capability_mode != "mocked" or snapshot.canonical_error is not None:
                raise ValidationError("calendar provider returned an invalid Foundation envelope")
            candidate = self.scheduler.propose(
                ScheduleRequest(
                    duration_minutes=duration,
                    deadline=fact.occurs_at,
                    buffer_before_minutes=self.BUFFER_MINUTES,
                    buffer_after_minutes=self.BUFFER_MINUTES,
                ),
                snapshot,
                hard_blocks=self._hard_blocks(uow, command.user_id),
            )
            if candidate is None:
                commitment.wait(
                    reason="No feasible mock-calendar slot before the confirmed deadline.",
                    review_at=now + timedelta(days=1),
                )
                uow.commitments.add(commitment)
                self._audit(
                    uow,
                    command,
                    "schedule.no_feasible_proposal",
                    "commitment",
                    commitment.id,
                    commitment.version,
                    "No hard-constraint-safe candidate was available.",
                    SourceType.SYSTEM_INFERRED,
                    snapshot.provenance.source_identifier,
                )
                self._record_capture_receipt(
                    uow, command, request_digest, intent, commitment, None, now
                )
                uow.commit()
                return CaptureIntentResult(intent, commitment, None)

            proposal_provenance = Provenance(
                source_type=SourceType.SYSTEM_INFERRED,
                source_identifier=f"scheduler:{candidate.input_snapshot_hash}",
                observed_at=snapshot.observed_at,
                recorded_at=now,
                confidence=min(
                    commitment.provenance.confidence,
                    snapshot.provenance.confidence,
                ),
                confirmation_status=ConfirmationStatus.UNCONFIRMED,
                sensitivity=Sensitivity.PERSONAL,
                actor_id=self.SYSTEM_ACTOR,
                data_subject_id=command.user_id,
                controller_id=command.user_id,
                correlation_id=command.correlation_id,
                valid_until=fact.occurs_at,
                input_references=(
                    commitment.provenance.source_identifier,
                    snapshot.provenance.source_identifier,
                ),
            )
            proposal = ScheduleProposal(
                id=self.id_factory(),
                user_id=command.user_id,
                commitment_id=commitment.id,
                starts_at=candidate.starts_at,
                ends_at=candidate.ends_at,
                status=ProposalStatus.PROPOSED,
                rationale=candidate.rationale,
                input_snapshot_hash=candidate.input_snapshot_hash,
                revision=1,
                created_at=now,
                provenance=proposal_provenance,
                calendar_provider_id=snapshot.provider_id,
                calendar_snapshot_version=snapshot.version,
            )
            uow.proposals.add(proposal)
            self._audit(
                uow,
                command,
                "schedule.proposed",
                "schedule_proposal",
                proposal.id,
                proposal.version,
                "Deterministic scheduler proposed a buffered mock-calendar slot.",
                SourceType.SYSTEM_INFERRED,
                proposal_provenance.source_identifier,
                {
                    "calendar_snapshot": snapshot.version,
                    "calendar_provider": snapshot.provider_id,
                },
            )
            self._record_capture_receipt(
                uow, command, request_digest, intent, commitment, proposal, now
            )
            uow.commit()
            return CaptureIntentResult(intent, commitment, proposal)

    def decide_proposal(self, command: DecideProposalCommand) -> DecideProposalResult:
        now = self.clock()
        with self.uow_factory() as uow:
            proposal = uow.proposals.get(command.proposal_id)
            if proposal is None:
                raise NotFoundError("proposal not found")
            context = AuthContext(command.user_id, "decide schedule proposal")
            self._authorize(
                uow,
                command,
                context,
                "schedule.proposal.decide.own",
                ResourceRef("schedule_proposal", proposal.id, proposal.user_id, "personal"),
            )
            request_digest = self._decision_request_digest(command, proposal)
            receipt = uow.receipts.get(command.idempotency_key)
            if receipt is not None:
                self._validate_receipt(
                    uow,
                    command,
                    receipt,
                    "decide_schedule_proposal",
                    request_digest,
                )
                return self._replay_decision(uow, receipt)

            commitment = uow.commitments.get(proposal.commitment_id)
            if commitment is None:
                raise NotFoundError("commitment not found")
            original_proposal_version = proposal.version
            original_commitment_version = commitment.version
            action_digest = self._approval_action_digest(
                command,
                proposal,
                commitment,
                original_commitment_version,
            )

            if command.decision is ProposalDecision.APPROVE:
                approval_calendar_context = self._provider_context(
                    command,
                    capability="calendar.availability.read.mock",
                    purpose="revalidate an approved internal schedule proposal",
                    deadline_at=commitment.due_at,
                    task_type="schedule_approval_revalidation",
                    risk="medium",
                    privacy="personal",
                )
                self._authorize(
                    uow,
                    command,
                    context,
                    "provider.calendar.availability.read.mock.own",
                    ResourceRef(
                        "provider_capability",
                        approval_calendar_context.capability,
                        command.user_id,
                        "personal",
                    ),
                )
                current_snapshot = self.calendar_provider.availability(
                    user_id=command.user_id,
                    before_iso=commitment.due_at.isoformat(),
                    context=approval_calendar_context,
                )
                if (
                    current_snapshot.capability_mode != "mocked"
                    or current_snapshot.canonical_error is not None
                ):
                    raise ValidationError(
                        "calendar provider returned an invalid Foundation envelope"
                    )
                if self._proposal_snapshot_hash(
                    proposal, commitment, current_snapshot
                ) != proposal.input_snapshot_hash or not self._proposal_fits_snapshot(
                    proposal, commitment, current_snapshot
                ):
                    self._deny_conflict(
                        uow,
                        command,
                        proposal,
                        "calendar availability changed; request a recalculation",
                        "denied:stale-calendar-snapshot",
                    )
                for block in uow.blocks.list_for_user(command.user_id):
                    if block.status is BlockStatus.CONFIRMED and intervals_overlap(
                        proposal.starts_at,
                        proposal.ends_at,
                        block.starts_at,
                        block.ends_at,
                    ):
                        self._deny_conflict(
                            uow,
                            command,
                            proposal,
                            "proposal conflicts with a confirmed block; request a recalculation",
                            "denied:schedule-overlap",
                        )
                try:
                    proposal.approve(command.expected_version)
                except (ConflictError, InvalidTransitionError) as exc:
                    self._deny_conflict(
                        uow,
                        command,
                        proposal,
                        str(exc),
                        "denied:stale-or-invalid-proposal",
                    )
                block = ScheduleBlock(
                    id=self.id_factory(),
                    user_id=command.user_id,
                    commitment_id=commitment.id,
                    starts_at=proposal.starts_at,
                    ends_at=proposal.ends_at,
                    status=BlockStatus.CONFIRMED,
                    created_at=now,
                )
                try:
                    commitment.schedule(block.id)
                    approval = self._approval(
                        command,
                        proposal,
                        commitment,
                        ApprovalStatus.APPROVED,
                        action_digest,
                        original_proposal_version,
                        original_commitment_version,
                        now,
                    )
                    uow.proposals.add(proposal)
                    uow.commitments.add(commitment)
                    uow.approvals.add(approval)
                    self._record_decision_receipt(
                        uow, command, request_digest, proposal, None, commitment, now
                    )
                    self._audit(
                        uow,
                        command,
                        "schedule.approved",
                        "schedule_proposal",
                        proposal.id,
                        proposal.version,
                        "User approved one reversible internal schedule block.",
                        SourceType.USER_STATED,
                        f"decision:{command.idempotency_key}",
                        {
                            "block_id": block.id,
                            "action_digest": action_digest,
                            "policy_version": self.policy.VERSION,
                        },
                        approval_id=approval.id,
                    )
                    # Add the block last so a persistent uniqueness guard remains the
                    # final authority when two approvals race past the read check.
                    uow.blocks.add(block)
                    uow.commit()
                except (ConflictError, InvalidTransitionError) as exc:
                    # The failed approval transaction also contained its staged success
                    # audit, so rollback it completely and record the denial in a fresh
                    # transaction after the database has released the losing write.
                    uow.rollback()
                    self._record_post_rollback_decision_denial(
                        command,
                        proposal_id=proposal.id,
                        proposal_version=original_proposal_version,
                        reason=str(exc),
                    )
                    raise ConflictError(str(exc)) from exc
                return DecideProposalResult(proposal, None, commitment)

            if command.decision is ProposalDecision.REJECT:
                try:
                    proposal.reject(command.expected_version)
                except (ConflictError, InvalidTransitionError) as exc:
                    self._deny_conflict(
                        uow,
                        command,
                        proposal,
                        str(exc),
                        "denied:stale-or-invalid-proposal",
                    )
                commitment.wait(
                    reason="User rejected the current schedule proposal.",
                    review_at=now + timedelta(days=7),
                )
                approval = self._approval(
                    command,
                    proposal,
                    commitment,
                    ApprovalStatus.REJECTED,
                    action_digest,
                    original_proposal_version,
                    original_commitment_version,
                    now,
                )
                uow.proposals.add(proposal)
                uow.commitments.add(commitment)
                uow.approvals.add(approval)
                self._record_decision_receipt(
                    uow, command, request_digest, proposal, None, commitment, now
                )
                self._audit(
                    uow,
                    command,
                    "schedule.rejected",
                    "schedule_proposal",
                    proposal.id,
                    proposal.version,
                    "User rejection was preserved; the commitment remains waiting.",
                    SourceType.USER_STATED,
                    f"decision:{command.idempotency_key}",
                    {
                        "action_digest": action_digest,
                        "policy_version": self.policy.VERSION,
                    },
                    approval_id=approval.id,
                )
                uow.commit()
                return DecideProposalResult(proposal, None, commitment)

            try:
                proposal.supersede(command.expected_version)
            except (ConflictError, InvalidTransitionError) as exc:
                self._deny_conflict(
                    uow,
                    command,
                    proposal,
                    str(exc),
                    "denied:stale-or-invalid-proposal",
                )
            calendar_context = self._provider_context(
                command,
                capability="calendar.availability.read.mock",
                purpose="recalculate a user-overridden internal schedule proposal",
                deadline_at=commitment.due_at,
                task_type="schedule_recalculation",
                risk="medium",
                privacy="personal",
            )
            self._authorize(
                uow,
                command,
                context,
                "provider.calendar.availability.read.mock.own",
                ResourceRef(
                    "provider_capability",
                    calendar_context.capability,
                    command.user_id,
                    "personal",
                ),
            )
            snapshot = self.calendar_provider.availability(
                user_id=command.user_id,
                before_iso=commitment.due_at.isoformat(),
                context=calendar_context,
            )
            if snapshot.capability_mode != "mocked" or snapshot.canonical_error is not None:
                raise ValidationError("calendar provider returned an invalid Foundation envelope")
            candidate = self.scheduler.propose(
                ScheduleRequest(
                    duration_minutes=commitment.duration_minutes,
                    deadline=commitment.due_at,
                    buffer_before_minutes=self.BUFFER_MINUTES,
                    buffer_after_minutes=self.BUFFER_MINUTES,
                    excluded_starts=(proposal.starts_at,),
                ),
                snapshot,
                hard_blocks=self._hard_blocks(uow, command.user_id),
            )
            if candidate is None:
                self._deny_conflict(
                    uow,
                    command,
                    proposal,
                    "no alternative feasible slot is available",
                    "denied:no-feasible-alternative",
                )
            replacement_provenance = Provenance(
                source_type=SourceType.SYSTEM_INFERRED,
                source_identifier=f"scheduler:{candidate.input_snapshot_hash}",
                observed_at=snapshot.observed_at,
                recorded_at=now,
                confidence=min(
                    commitment.provenance.confidence,
                    snapshot.provenance.confidence,
                ),
                confirmation_status=ConfirmationStatus.UNCONFIRMED,
                sensitivity=Sensitivity.PERSONAL,
                actor_id=self.SYSTEM_ACTOR,
                data_subject_id=command.user_id,
                controller_id=command.user_id,
                correlation_id=command.correlation_id,
                valid_until=commitment.due_at,
                input_references=(
                    commitment.provenance.source_identifier,
                    snapshot.provenance.source_identifier,
                ),
                supersedes_reference=proposal.provenance.source_identifier,
            )
            replacement = ScheduleProposal(
                id=self.id_factory(),
                user_id=command.user_id,
                commitment_id=commitment.id,
                starts_at=candidate.starts_at,
                ends_at=candidate.ends_at,
                status=ProposalStatus.PROPOSED,
                rationale="Recalculated after the user requested a change. " + candidate.rationale,
                input_snapshot_hash=candidate.input_snapshot_hash,
                revision=proposal.revision + 1,
                created_at=now,
                provenance=replacement_provenance,
                calendar_provider_id=snapshot.provider_id,
                calendar_snapshot_version=snapshot.version,
                supersedes_id=proposal.id,
            )
            approval = self._approval(
                command,
                proposal,
                commitment,
                ApprovalStatus.APPROVED,
                action_digest,
                original_proposal_version,
                original_commitment_version,
                now,
            )
            uow.proposals.add(proposal)
            uow.proposals.add(replacement)
            uow.approvals.add(approval)
            self._record_decision_receipt(
                uow, command, request_digest, proposal, replacement, commitment, now
            )
            self._audit(
                uow,
                command,
                "schedule.changed",
                "schedule_proposal",
                replacement.id,
                replacement.version,
                "Old revision was superseded and recalculated from current mock availability.",
                SourceType.SYSTEM_INFERRED,
                replacement_provenance.source_identifier,
                {
                    "supersedes_id": proposal.id,
                    "action_digest": action_digest,
                    "policy_version": self.policy.VERSION,
                },
                approval_id=approval.id,
            )
            uow.commit()
            return DecideProposalResult(proposal, replacement, commitment)

    def _approval(
        self,
        command: DecideProposalCommand,
        proposal: ScheduleProposal,
        commitment: Commitment,
        status: ApprovalStatus,
        digest: str,
        proposal_version: int,
        commitment_version: int,
        now: datetime,
    ) -> Approval:
        return Approval(
            id=self.id_factory(),
            user_id=command.user_id,
            requester_id=self.SYSTEM_ACTOR,
            approver_id=command.user_id,
            proposal_id=proposal.id,
            permission="schedule.proposal.decide.own",
            action_level=3,
            environment="development-mock",
            target_type="schedule_proposal",
            target_id=proposal.id,
            input_snapshot_hash=proposal.input_snapshot_hash,
            calendar_provider_id=proposal.calendar_provider_id,
            calendar_snapshot_version=proposal.calendar_snapshot_version,
            provider_id="internal:none",
            on_behalf_of_id=command.user_id,
            disclosed_data="none",
            audience="local user only",
            reversible=True,
            expected_consequence=self._expected_consequence(command.decision, commitment),
            status=status,
            action_digest=digest,
            proposal_version=proposal_version,
            commitment_version=commitment_version,
            policy_version=self.policy.VERSION,
            expires_at=now + timedelta(minutes=15),
            nonce=self.id_factory(),
            idempotency_key=command.idempotency_key,
            created_at=now,
            consumed_at=now,
        )

    @staticmethod
    def _expected_consequence(decision: ProposalDecision, commitment: Commitment) -> str:
        if decision is ProposalDecision.APPROVE:
            return f"create one internal block and schedule commitment {commitment.id}"
        if decision is ProposalDecision.REJECT:
            return f"reject proposal and keep commitment {commitment.id} waiting"
        return f"supersede proposal and create one replacement for commitment {commitment.id}"

    def _approval_action_digest(
        self,
        command: DecideProposalCommand,
        proposal: ScheduleProposal,
        commitment: Commitment,
        commitment_version: int,
    ) -> str:
        payload = {
            "decision": command.decision.value,
            "environment": "development-mock",
            "permission": "schedule.proposal.decide.own",
            "policy_version": self.policy.VERSION,
            "action_level": 3,
            "requester_id": self.SYSTEM_ACTOR,
            "on_behalf_of_id": command.user_id,
            "approver_id": command.user_id,
            "provider_id": "internal:none",
            "audience": "local user only",
            "disclosed_data": "none",
            "reversible": True,
            "proposal_id": proposal.id,
            "proposal_version": command.expected_version,
            "input_snapshot_hash": proposal.input_snapshot_hash,
            "calendar_provider_id": proposal.calendar_provider_id,
            "calendar_snapshot_version": proposal.calendar_snapshot_version,
            "commitment_id": commitment.id,
            "commitment_version": commitment_version,
            "requested_start": (
                command.requested_start.isoformat() if command.requested_start else None
            ),
            "starts_at": proposal.starts_at.isoformat(),
            "ends_at": proposal.ends_at.isoformat(),
            "user_id": command.user_id,
        }
        return self._digest(payload)

    @classmethod
    def _capture_request_digest(cls, command: CaptureIntentCommand) -> str:
        return cls._digest(
            {
                "command_type": "capture_intent",
                "raw_text": command.raw_text,
                "user_id": command.user_id,
            }
        )

    @classmethod
    def _decision_request_digest(
        cls, command: DecideProposalCommand, proposal: ScheduleProposal
    ) -> str:
        return cls._digest(
            {
                "command_type": "decide_schedule_proposal",
                "decision": command.decision.value,
                "proposal_id": proposal.id,
                "expected_version": command.expected_version,
                "requested_start": (
                    command.requested_start.isoformat() if command.requested_start else None
                ),
                "starts_at": proposal.starts_at.isoformat(),
                "ends_at": proposal.ends_at.isoformat(),
                "user_id": command.user_id,
            }
        )

    @staticmethod
    def _digest(payload: Mapping[str, object]) -> str:
        return sha256(
            json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
        ).hexdigest()

    def _validate_receipt(
        self,
        uow: UnitOfWork,
        command: CaptureIntentCommand | DecideProposalCommand,
        receipt: CommandReceipt,
        command_type: str,
        request_digest: str,
    ) -> None:
        if (
            receipt.user_id != command.user_id
            or receipt.command_type != command_type
            or receipt.request_digest != request_digest
        ):
            self._audit_denial(
                uow,
                command,
                action="command.idempotency_reuse_denied",
                entity_type="command_receipt",
                entity_id="protected-idempotency-key",
                entity_version=0,
                summary="Idempotency-key reuse with changed command content was denied.",
                policy_result="denied:idempotency-key-reuse",
            )
            uow.commit()
            raise ConflictError("idempotency key was already used for a different command")

    @staticmethod
    def _replay_capture(uow: UnitOfWork, receipt: CommandReceipt) -> CaptureIntentResult:
        if receipt.intent_id is None:
            raise ConflictError("capture receipt is missing its result reference")
        intent = uow.intents.get(receipt.intent_id)
        commitment = uow.commitments.get(receipt.commitment_id) if receipt.commitment_id else None
        proposal = uow.proposals.get(receipt.proposal_id) if receipt.proposal_id else None
        if intent is None or (receipt.commitment_id and commitment is None):
            raise ConflictError("capture receipt refers to missing authoritative state")
        if receipt.proposal_id and proposal is None:
            raise ConflictError("capture receipt refers to a missing proposal")
        return CaptureIntentResult(intent, commitment, proposal)

    @staticmethod
    def _replay_decision(uow: UnitOfWork, receipt: CommandReceipt) -> DecideProposalResult:
        if receipt.proposal_id is None or receipt.commitment_id is None:
            raise ConflictError("decision receipt is missing its result reference")
        proposal = uow.proposals.get(receipt.proposal_id)
        commitment = uow.commitments.get(receipt.commitment_id)
        replacement = (
            uow.proposals.get(receipt.replacement_proposal_id)
            if receipt.replacement_proposal_id
            else None
        )
        if proposal is None or commitment is None:
            raise ConflictError("decision receipt refers to missing authoritative state")
        if receipt.replacement_proposal_id and replacement is None:
            raise ConflictError("decision receipt refers to a missing replacement")
        return DecideProposalResult(proposal, replacement, commitment)

    @staticmethod
    def _record_capture_receipt(
        uow: UnitOfWork,
        command: CaptureIntentCommand,
        request_digest: str,
        intent: Intent,
        commitment: Commitment | None,
        proposal: ScheduleProposal | None,
        now: datetime,
    ) -> None:
        uow.receipts.add(
            CommandReceipt(
                idempotency_key=command.idempotency_key,
                user_id=command.user_id,
                command_type="capture_intent",
                request_digest=request_digest,
                created_at=now,
                intent_id=intent.id,
                commitment_id=commitment.id if commitment else None,
                proposal_id=proposal.id if proposal else None,
            )
        )

    @staticmethod
    def _record_decision_receipt(
        uow: UnitOfWork,
        command: DecideProposalCommand,
        request_digest: str,
        proposal: ScheduleProposal,
        replacement: ScheduleProposal | None,
        commitment: Commitment,
        now: datetime,
    ) -> None:
        uow.receipts.add(
            CommandReceipt(
                idempotency_key=command.idempotency_key,
                user_id=command.user_id,
                command_type="decide_schedule_proposal",
                request_digest=request_digest,
                created_at=now,
                commitment_id=commitment.id,
                proposal_id=proposal.id,
                replacement_proposal_id=replacement.id if replacement else None,
            )
        )

    @staticmethod
    def _hard_blocks(uow: UnitOfWork, user_id: str) -> tuple[AvailabilitySlot, ...]:
        return tuple(
            AvailabilitySlot(block.starts_at, block.ends_at)
            for block in uow.blocks.list_for_user(user_id)
            if block.status is BlockStatus.CONFIRMED
        )

    @staticmethod
    def _proposal_snapshot_hash(
        proposal: ScheduleProposal,
        commitment: Commitment,
        snapshot: CalendarSnapshot,
    ) -> str:
        digest_input = (
            f"{snapshot.provider_id}|{snapshot.version}|{commitment.duration_minutes}|"
            f"{commitment.due_at.isoformat()}|{proposal.starts_at.isoformat()}|"
            f"{proposal.ends_at.isoformat()}"
        )
        return sha256(digest_input.encode()).hexdigest()

    def _proposal_fits_snapshot(
        self,
        proposal: ScheduleProposal,
        commitment: Commitment,
        snapshot: CalendarSnapshot,
    ) -> bool:
        before = timedelta(minutes=self.BUFFER_MINUTES)
        after = timedelta(minutes=self.BUFFER_MINUTES)
        return proposal.ends_at <= commitment.due_at and any(
            proposal.starts_at - before >= slot.starts_at
            and proposal.ends_at + after <= slot.ends_at
            for slot in snapshot.slots
        )

    def _authorize(
        self,
        uow: UnitOfWork,
        command: CaptureIntentCommand | DecideProposalCommand,
        context: AuthContext,
        permission: str,
        resource: ResourceRef,
    ) -> str:
        decision = self.policy.decide(context, permission, resource)
        if decision.allowed:
            return decision.rule_id
        self._audit_denial(
            uow,
            command,
            action="authorization.denied",
            entity_type=resource.resource_type,
            entity_id="protected-resource",
            entity_version=0,
            summary="A command or provider capability was denied before execution.",
            policy_result=f"denied:{decision.rule_id}",
        )
        uow.commit()
        raise AuthorizationError("resource not found")

    def _deny_conflict(
        self,
        uow: UnitOfWork,
        command: DecideProposalCommand,
        proposal: ScheduleProposal,
        reason: str,
        policy_result: str,
    ) -> Never:
        self._audit_denial(
            uow,
            command,
            action="schedule.decision_denied",
            entity_type="schedule_proposal",
            entity_id=proposal.id,
            entity_version=proposal.version,
            summary=reason,
            policy_result=policy_result,
        )
        uow.commit()
        raise ConflictError(reason)

    def _record_post_rollback_decision_denial(
        self,
        command: DecideProposalCommand,
        *,
        proposal_id: str,
        proposal_version: int,
        reason: str,
    ) -> None:
        """Persist a race denial after the failed approval transaction was rolled back."""
        with self.uow_factory() as denial_uow:
            self._audit_denial(
                denial_uow,
                command,
                action="schedule.decision_denied",
                entity_type="schedule_proposal",
                entity_id=proposal_id,
                entity_version=proposal_version,
                summary=reason,
                policy_result="denied:concurrent-or-duplicate-write",
            )
            denial_uow.commit()

    def _audit_denial(
        self,
        uow: UnitOfWork,
        command: CaptureIntentCommand | DecideProposalCommand,
        *,
        action: str,
        entity_type: str,
        entity_id: str,
        entity_version: int,
        summary: str,
        policy_result: str,
    ) -> None:
        uow.audit.append(
            AuditEvent(
                id=self.id_factory(),
                user_id=command.user_id,
                action=action,
                entity_type=entity_type,
                entity_id=entity_id,
                correlation_id=command.correlation_id,
                occurred_at=self.clock(),
                outcome="denied",
                source_type=SourceType.USER_STATED.value,
                source_identifier=f"command:{command.idempotency_key}",
                actor_id=command.user_id,
                on_behalf_of_id=None,
                entity_version=entity_version,
                causation_id=command.idempotency_key,
                policy_result=policy_result,
                capability_mode=self.CAPABILITY_MODE,
                summary=summary,
                details={},
            )
        )

    def _provider_context(
        self,
        command: CaptureIntentCommand | DecideProposalCommand,
        *,
        capability: str,
        purpose: str,
        deadline_at: datetime,
        task_type: str,
        risk: str,
        privacy: str,
    ) -> ProviderRequestContext:
        return ProviderRequestContext(
            actor_id=self.SYSTEM_ACTOR,
            on_behalf_of_id=command.user_id,
            correlation_id=command.correlation_id,
            capability=capability,
            purpose=purpose,
            deadline_at=deadline_at,
            idempotency_key=command.idempotency_key,
            task_type=task_type,
            risk=risk,
            privacy=privacy,
        )

    def _audit(
        self,
        uow: UnitOfWork,
        command: CaptureIntentCommand | DecideProposalCommand,
        action: str,
        entity_type: str,
        entity_id: str,
        entity_version: int,
        summary: str,
        source_type: SourceType,
        source_identifier: str,
        details: dict[str, str | int | float | bool | None] | None = None,
        *,
        approval_id: str | None = None,
    ) -> None:
        actor_id = command.user_id if source_type is SourceType.USER_STATED else self.SYSTEM_ACTOR
        on_behalf_of_id = None if actor_id == command.user_id else command.user_id
        uow.audit.append(
            AuditEvent(
                id=self.id_factory(),
                user_id=command.user_id,
                action=action,
                entity_type=entity_type,
                entity_id=entity_id,
                correlation_id=command.correlation_id,
                occurred_at=self.clock(),
                outcome="succeeded",
                source_type=source_type.value,
                source_identifier=source_identifier,
                actor_id=actor_id,
                on_behalf_of_id=on_behalf_of_id,
                entity_version=entity_version,
                causation_id=command.idempotency_key,
                policy_result=f"allowed:{self.policy.VERSION}",
                capability_mode=self.CAPABILITY_MODE,
                approval_id=approval_id,
                agent_reference=self.SYSTEM_ACTOR,
                summary=summary,
                details=details or {},
            )
        )
