from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from hashlib import sha256

from personal_os.domain.errors import ValidationError
from personal_os.domain.provenance import Provenance, require_aware


@dataclass(frozen=True, slots=True)
class AvailabilitySlot:
    starts_at: datetime
    ends_at: datetime

    def __post_init__(self) -> None:
        require_aware(self.starts_at, "starts_at")
        require_aware(self.ends_at, "ends_at")
        if self.ends_at <= self.starts_at:
            raise ValidationError("availability end must be after start")


@dataclass(frozen=True, slots=True)
class CalendarSnapshot:
    provider_id: str
    version: str
    observed_at: datetime
    slots: tuple[AvailabilitySlot, ...]
    provenance: Provenance
    capability_mode: str = "mocked"
    external_reference: str = "synthetic:calendar-snapshot"
    warnings: tuple[str, ...] = ()
    canonical_error: str | None = None


@dataclass(frozen=True, slots=True)
class ScheduleRequest:
    duration_minutes: int
    deadline: datetime
    buffer_before_minutes: int = 15
    buffer_after_minutes: int = 15
    excluded_starts: tuple[datetime, ...] = ()


@dataclass(frozen=True, slots=True)
class ScheduleCandidate:
    starts_at: datetime
    ends_at: datetime
    rationale: str
    input_snapshot_hash: str


def intervals_overlap(
    first_start: datetime,
    first_end: datetime,
    second_start: datetime,
    second_end: datetime,
) -> bool:
    return first_start < second_end and second_start < first_end


class DeterministicScheduler:
    """Feasibility-first scheduler; it never invents or relaxes hard constraints."""

    def propose(
        self,
        request: ScheduleRequest,
        snapshot: CalendarSnapshot,
        hard_blocks: tuple[AvailabilitySlot, ...] = (),
    ) -> ScheduleCandidate | None:
        require_aware(request.deadline, "deadline")
        if request.duration_minutes <= 0:
            raise ValidationError("duration must be positive")

        duration = timedelta(minutes=request.duration_minutes)
        before = timedelta(minutes=request.buffer_before_minutes)
        after = timedelta(minutes=request.buffer_after_minutes)
        excluded = set(request.excluded_starts)
        candidates: list[tuple[datetime, datetime]] = []

        for slot in snapshot.slots:
            starts_at = slot.starts_at + before
            ends_at = starts_at + duration
            if (
                starts_at in excluded
                or ends_at + after > slot.ends_at
                or ends_at > request.deadline
            ):
                continue
            if any(
                intervals_overlap(
                    starts_at - before, ends_at + after, block.starts_at, block.ends_at
                )
                for block in hard_blocks
            ):
                continue
            candidates.append((starts_at, ends_at))

        if not candidates:
            return None

        starts_at, ends_at = sorted(candidates, key=lambda pair: pair[0])[0]
        digest_input = (
            f"{snapshot.provider_id}|{snapshot.version}|{request.duration_minutes}|"
            f"{request.deadline.isoformat()}|{starts_at.isoformat()}|{ends_at.isoformat()}"
        )
        return ScheduleCandidate(
            starts_at=starts_at,
            ends_at=ends_at,
            rationale=(
                f"Earliest feasible mock-calendar window before the deadline, preserving "
                f"{request.buffer_before_minutes}-minute and "
                f"{request.buffer_after_minutes}-minute buffers."
            ),
            input_snapshot_hash=sha256(digest_input.encode()).hexdigest(),
        )
