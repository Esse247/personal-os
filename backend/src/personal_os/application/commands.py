from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum

from personal_os.domain.entities import Commitment, Intent, ScheduleProposal


class ProposalDecision(StrEnum):
    APPROVE = "approve"
    CHANGE = "change"
    REJECT = "reject"


@dataclass(frozen=True, slots=True)
class CaptureIntentCommand:
    user_id: str
    raw_text: str
    correlation_id: str
    idempotency_key: str


@dataclass(frozen=True, slots=True)
class CaptureIntentResult:
    intent: Intent
    commitment: Commitment | None
    proposal: ScheduleProposal | None


@dataclass(frozen=True, slots=True)
class DecideProposalCommand:
    user_id: str
    proposal_id: str
    decision: ProposalDecision
    expected_version: int
    correlation_id: str
    idempotency_key: str
    requested_start: datetime | None = None


@dataclass(frozen=True, slots=True)
class DecideProposalResult:
    proposal: ScheduleProposal
    replacement: ScheduleProposal | None
    commitment: Commitment
