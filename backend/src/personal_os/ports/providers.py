from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Protocol

from personal_os.domain.provenance import Provenance
from personal_os.domain.scheduling import CalendarSnapshot


@dataclass(frozen=True, slots=True)
class ProviderRequestContext:
    actor_id: str
    on_behalf_of_id: str
    correlation_id: str
    capability: str
    purpose: str
    deadline_at: datetime
    idempotency_key: str
    task_type: str
    risk: str
    privacy: str


@dataclass(frozen=True, slots=True)
class InterpretationProposal:
    title: str | None
    related_fact_label: str | None
    duration_minutes: int | None
    missing_fields: tuple[str, ...]
    clarification_question: str | None
    provider_id: str
    observed_at: datetime
    provenance: Provenance
    capability_mode: str = "mocked"
    external_reference: str = "synthetic:model-interpretation"
    external_version: str = "v1"
    warnings: tuple[str, ...] = ()
    canonical_error: str | None = None


@dataclass(frozen=True, slots=True)
class ProviderResult[ProviderValue]:
    value: ProviderValue
    provider_id: str
    capability_mode: str
    external_reference: str
    external_version: str
    observed_at: datetime
    provenance: Provenance
    warnings: tuple[str, ...] = ()
    canonical_error: str | None = None


class ModelProvider(Protocol):
    provider_id: str

    def interpret_intent(
        self, *, raw_text: str, context: ProviderRequestContext
    ) -> InterpretationProposal: ...


class CalendarProvider(Protocol):
    provider_id: str

    def availability(
        self, *, user_id: str, before_iso: str, context: ProviderRequestContext
    ) -> CalendarSnapshot: ...


class NotificationProvider(Protocol):
    def record_mock_notification(
        self, *, user_id: str, summary: str, context: ProviderRequestContext
    ) -> ProviderResult[str]: ...


class EmailProvider(Protocol):
    def draft(
        self, *, subject: str, body: str, context: ProviderRequestContext
    ) -> ProviderResult[str]: ...


class BankingProvider(Protocol):
    def read_synthetic_transactions(
        self, *, user_id: str, context: ProviderRequestContext
    ) -> ProviderResult[tuple[dict[str, object], ...]]: ...


class WearableProvider(Protocol):
    def observations(
        self, *, user_id: str, context: ProviderRequestContext
    ) -> ProviderResult[tuple[dict[str, object], ...]]: ...


class LocationProvider(Protocol):
    def observations(
        self, *, user_id: str, context: ProviderRequestContext
    ) -> ProviderResult[tuple[dict[str, object], ...]]: ...


class VoiceProvider(Protocol):
    def transcribe_mock(
        self, *, audio_reference: str, context: ProviderRequestContext
    ) -> ProviderResult[str]: ...


class SearchProvider(Protocol):
    def search_mock(
        self, *, query: str, context: ProviderRequestContext
    ) -> ProviderResult[tuple[dict[str, object], ...]]: ...


class FileStorageProvider(Protocol):
    def put_mock(
        self, *, name: str, content: bytes, context: ProviderRequestContext
    ) -> ProviderResult[str]: ...


class ToolProvider(Protocol):
    def simulate(
        self,
        *,
        capability: str,
        payload: dict[str, object],
        context: ProviderRequestContext,
    ) -> ProviderResult[dict[str, object]]: ...
