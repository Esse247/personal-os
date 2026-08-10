from __future__ import annotations

from datetime import UTC, datetime

from personal_os.domain.provenance import (
    ConfirmationStatus,
    Provenance,
    Sensitivity,
    SourceType,
)
from personal_os.domain.scheduling import AvailabilitySlot, CalendarSnapshot
from personal_os.ports.providers import (
    InterpretationProposal,
    ProviderRequestContext,
    ProviderResult,
)


def mock_result[ProviderValue](
    provider_id: str,
    context: ProviderRequestContext,
    value: ProviderValue,
    *,
    sensitivity: Sensitivity = Sensitivity.PERSONAL,
    mode: str = "mocked",
    canonical_error: str | None = None,
) -> ProviderResult[ProviderValue]:
    observed_at = datetime(2026, 8, 10, 8, 0, tzinfo=UTC)
    return ProviderResult(
        value=value,
        provider_id=provider_id,
        capability_mode=mode,
        external_reference=f"synthetic:{provider_id}:{context.capability}",
        external_version="v1",
        observed_at=observed_at,
        provenance=Provenance(
            source_type=SourceType.TOOL_OBSERVED,
            source_identifier=f"synthetic:{provider_id}:{context.capability}",
            observed_at=observed_at,
            recorded_at=observed_at,
            confidence=1.0,
            confirmation_status=ConfirmationStatus.CONFIRMED,
            sensitivity=sensitivity,
            actor_id=context.actor_id,
            data_subject_id=context.on_behalf_of_id,
            controller_id=context.on_behalf_of_id,
            correlation_id=context.correlation_id,
            input_references=(f"request:{context.idempotency_key}",),
        ),
        canonical_error=canonical_error,
    )


class DeterministicMockModelProvider:
    provider_id = "deterministic-intent-mock-v1"

    def interpret_intent(
        self, *, raw_text: str, context: ProviderRequestContext
    ) -> InterpretationProposal:
        observed_at = datetime(2026, 8, 10, 8, 0, tzinfo=UTC)
        provenance = Provenance(
            source_type=SourceType.SYSTEM_INFERRED,
            source_identifier=f"{self.provider_id}:interpretation-v1",
            observed_at=observed_at,
            recorded_at=observed_at,
            confidence=1.0,
            confirmation_status=ConfirmationStatus.UNCONFIRMED,
            sensitivity=Sensitivity.PERSONAL,
            actor_id=context.actor_id,
            data_subject_id=context.on_behalf_of_id,
            controller_id=context.on_behalf_of_id,
            correlation_id=context.correlation_id,
            input_references=(f"capture:{context.idempotency_key}",),
        )
        normalised = " ".join(raw_text.casefold().split())
        if "haircut" in normalised and "wedding" in normalised:
            return InterpretationProposal(
                title="Arrange a haircut",
                related_fact_label="Wedding",
                duration_minutes=None,
                missing_fields=(),
                clarification_question=None,
                provider_id=self.provider_id,
                observed_at=observed_at,
                provenance=provenance,
            )
        return InterpretationProposal(
            title=None,
            related_fact_label=None,
            duration_minutes=None,
            missing_fields=("objective", "deadline", "duration"),
            clarification_question="What should be arranged, and what deadline should I use?",
            provider_id=self.provider_id,
            observed_at=observed_at,
            provenance=provenance,
        )


class AlternativeDeterministicMockModelProvider(DeterministicMockModelProvider):
    """Contract-equivalent mock used to prove provider substitution."""

    provider_id = "deterministic-intent-mock-alternative-v1"


class DeterministicMockCalendarProvider:
    provider_id = "synthetic-calendar-v1"

    def availability(
        self, *, user_id: str, before_iso: str, context: ProviderRequestContext
    ) -> CalendarSnapshot:
        del before_iso
        observed_at = datetime(2026, 8, 10, 8, 0, tzinfo=UTC)
        provenance = Provenance(
            source_type=SourceType.TOOL_OBSERVED,
            source_identifier="synthetic-calendar-fixture:availability-v1",
            observed_at=observed_at,
            recorded_at=observed_at,
            confidence=1.0,
            confirmation_status=ConfirmationStatus.CONFIRMED,
            sensitivity=Sensitivity.PERSONAL,
            actor_id=context.actor_id,
            data_subject_id=user_id,
            controller_id=user_id,
            correlation_id=context.correlation_id,
            input_references=(f"request:{context.idempotency_key}",),
        )
        return CalendarSnapshot(
            provider_id=self.provider_id,
            version="availability-snapshot-v1",
            observed_at=observed_at,
            slots=(
                AvailabilitySlot(
                    datetime(2026, 9, 10, 9, 0, tzinfo=UTC),
                    datetime(2026, 9, 10, 11, 0, tzinfo=UTC),
                ),
                AvailabilitySlot(
                    datetime(2026, 9, 12, 13, 0, tzinfo=UTC),
                    datetime(2026, 9, 12, 15, 0, tzinfo=UTC),
                ),
                AvailabilitySlot(
                    datetime(2026, 9, 16, 10, 0, tzinfo=UTC),
                    datetime(2026, 9, 16, 12, 0, tzinfo=UTC),
                ),
            ),
            provenance=provenance,
        )


class AlternativeMockCalendarProvider(DeterministicMockCalendarProvider):
    provider_id = "synthetic-calendar-alternative-v1"


class SyntheticBankingProvider:
    provider_id = "synthetic-banking-v1"

    def read_synthetic_transactions(
        self, *, user_id: str, context: ProviderRequestContext
    ) -> ProviderResult[tuple[dict[str, object], ...]]:
        return mock_result(
            self.provider_id,
            context,
            (
                {
                    "user_id": user_id,
                    "source_id": "synthetic-bank-transaction-001",
                    "merchant": "Northstar Timber Yard",
                    "memo": "Timber delivery · synthetic fixture",
                    "amount_minor": -245000,
                    "currency": "GBP",
                },
            ),
            sensitivity=Sensitivity.FINANCIAL,
        )


class NullNotificationProvider:
    provider_id = "null-notification-v1"

    def record_mock_notification(
        self, *, user_id: str, summary: str, context: ProviderRequestContext
    ) -> ProviderResult[str]:
        return mock_result(self.provider_id, context, f"mock-notification:{user_id}:{len(summary)}")


class NullEmailProvider:
    provider_id = "null-email-v1"

    def draft(
        self, *, subject: str, body: str, context: ProviderRequestContext
    ) -> ProviderResult[str]:
        return mock_result(
            self.provider_id, context, f"mock-email-draft:{len(subject)}:{len(body)}"
        )


class NullObservationProvider:
    provider_id = "null-observation-v1"

    def observations(
        self, *, user_id: str, context: ProviderRequestContext
    ) -> ProviderResult[tuple[dict[str, object], ...]]:
        del user_id
        return mock_result(self.provider_id, context, ())


class NullVoiceProvider:
    provider_id = "null-voice-v1"

    def transcribe_mock(
        self, *, audio_reference: str, context: ProviderRequestContext
    ) -> ProviderResult[str]:
        return mock_result(self.provider_id, context, f"Synthetic transcript for {audio_reference}")


class NullSearchProvider:
    provider_id = "null-search-v1"

    def search_mock(
        self, *, query: str, context: ProviderRequestContext
    ) -> ProviderResult[tuple[dict[str, object], ...]]:
        del query
        return mock_result(self.provider_id, context, ())


class NullFileStorageProvider:
    provider_id = "null-file-storage-v1"

    def put_mock(
        self, *, name: str, content: bytes, context: ProviderRequestContext
    ) -> ProviderResult[str]:
        return mock_result(self.provider_id, context, f"mock-file:{name}:{len(content)}")


class NullToolProvider:
    provider_id = "null-tool-v1"

    def simulate(
        self,
        *,
        capability: str,
        payload: dict[str, object],
        context: ProviderRequestContext,
    ) -> ProviderResult[dict[str, object]]:
        if capability != "tool.simulate.safe":
            return mock_result(
                self.provider_id,
                context,
                {"capability": capability, "accepted": False},
                mode="prohibited",
                canonical_error="prohibited_capability",
            )
        return mock_result(
            self.provider_id,
            context,
            {"capability": capability, "accepted": bool(payload)},
        )
