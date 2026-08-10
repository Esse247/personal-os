from __future__ import annotations

from datetime import UTC, datetime

from personal_os.domain.entities import FinancialTransaction
from personal_os.domain.finance import DeterministicTransactionCategoriser
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
)

NOW = datetime(2026, 8, 10, 8, 0, tzinfo=UTC)


def provenance(sensitivity: Sensitivity) -> Provenance:
    return Provenance(
        source_type=SourceType.TOOL_OBSERVED,
        source_identifier="synthetic-test",
        observed_at=NOW,
        recorded_at=NOW,
        confidence=1,
        confirmation_status=ConfirmationStatus.CONFIRMED,
        sensitivity=sensitivity,
        actor_id="test-provider",
        data_subject_id="user-1",
        controller_id="user-1",
        correlation_id="test-correlation",
    )


def snapshot() -> CalendarSnapshot:
    return CalendarSnapshot(
        provider_id="calendar-mock",
        version="v1",
        observed_at=NOW,
        slots=(
            AvailabilitySlot(
                datetime(2026, 9, 10, 9, 0, tzinfo=UTC),
                datetime(2026, 9, 10, 11, 0, tzinfo=UTC),
            ),
            AvailabilitySlot(
                datetime(2026, 9, 12, 13, 0, tzinfo=UTC),
                datetime(2026, 9, 12, 15, 0, tzinfo=UTC),
            ),
        ),
        provenance=provenance(Sensitivity.PERSONAL),
    )


def test_scheduler_preserves_buffers_and_is_deterministic() -> None:
    scheduler = DeterministicScheduler()
    request = ScheduleRequest(
        duration_minutes=60,
        deadline=datetime(2026, 9, 19, 14, 0, tzinfo=UTC),
        buffer_before_minutes=15,
        buffer_after_minutes=15,
    )
    first = scheduler.propose(request, snapshot())
    second = scheduler.propose(request, snapshot())
    assert first == second
    assert first is not None
    assert first.starts_at == datetime(2026, 9, 10, 9, 15, tzinfo=UTC)
    assert first.ends_at == datetime(2026, 9, 10, 10, 15, tzinfo=UTC)


def test_scheduler_rejects_conflicts_and_infeasible_deadline() -> None:
    scheduler = DeterministicScheduler()
    request = ScheduleRequest(
        duration_minutes=60,
        deadline=datetime(2026, 9, 11, 8, 0, tzinfo=UTC),
    )
    hard_block = AvailabilitySlot(
        datetime(2026, 9, 10, 9, 0, tzinfo=UTC),
        datetime(2026, 9, 10, 11, 0, tzinfo=UTC),
    )
    assert scheduler.propose(request, snapshot(), (hard_block,)) is None


def test_user_change_excludes_rejected_start() -> None:
    scheduler = DeterministicScheduler()
    first_start = datetime(2026, 9, 10, 9, 15, tzinfo=UTC)
    result = scheduler.propose(
        ScheduleRequest(
            duration_minutes=60,
            deadline=datetime(2026, 9, 19, 14, 0, tzinfo=UTC),
            excluded_starts=(first_start,),
        ),
        snapshot(),
    )
    assert result is not None
    assert result.starts_at == datetime(2026, 9, 12, 13, 15, tzinfo=UTC)


def test_finance_categorisation_is_exact_and_does_not_mutate_source() -> None:
    transaction = FinancialTransaction(
        id="transaction-1",
        user_id="user-1",
        household_id="household-1",
        project_id="project-1",
        merchant="Northstar Timber Yard",
        memo="Timber delivery",
        amount_minor=-245000,
        currency="GBP",
        posted_at=NOW,
        provenance=provenance(Sensitivity.FINANCIAL),
        created_at=NOW,
    )
    result = DeterministicTransactionCategoriser().categorise(transaction)
    assert result.category == "House project · materials"
    assert result.confidence == 0.98
    assert transaction.amount_minor == -245000
    assert transaction.memo == "Timber delivery"
