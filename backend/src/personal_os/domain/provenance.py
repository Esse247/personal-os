from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime
from enum import StrEnum
from typing import Any

from personal_os.domain.errors import ValidationError


class SourceType(StrEnum):
    USER_STATED = "USER_STATED"
    TOOL_OBSERVED = "TOOL_OBSERVED"
    SYSTEM_INFERRED = "SYSTEM_INFERRED"
    SYSTEM_PREDICTED = "SYSTEM_PREDICTED"


class ConfirmationStatus(StrEnum):
    UNCONFIRMED = "unconfirmed"
    CONFIRMED = "confirmed"
    DISPUTED = "disputed"
    SUPERSEDED = "superseded"


class Sensitivity(StrEnum):
    PUBLIC = "public"
    HOUSEHOLD_SHARED = "household_shared"
    PERSONAL = "personal"
    FINANCIAL = "financial"
    HEALTH = "health"
    IDENTITY = "identity"
    LEGAL = "legal"
    CREDENTIAL = "credential"


def require_aware(value: datetime, field_name: str) -> None:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValidationError(f"{field_name} must be timezone-aware")


@dataclass(frozen=True, slots=True)
class Provenance:
    source_type: SourceType
    source_identifier: str
    observed_at: datetime
    recorded_at: datetime
    confidence: float
    confirmation_status: ConfirmationStatus
    sensitivity: Sensitivity
    actor_id: str
    data_subject_id: str
    controller_id: str
    correlation_id: str
    valid_from: datetime | None = None
    valid_until: datetime | None = None
    input_references: tuple[str, ...] = ()
    supersedes_reference: str | None = None

    def __post_init__(self) -> None:
        if not self.source_identifier.strip():
            raise ValidationError("source_identifier is required")
        for field_name in ("actor_id", "data_subject_id", "controller_id", "correlation_id"):
            if not getattr(self, field_name).strip():
                raise ValidationError(f"{field_name} is required")
        require_aware(self.observed_at, "observed_at")
        require_aware(self.recorded_at, "recorded_at")
        if not 0 <= self.confidence <= 1:
            raise ValidationError("confidence must be between 0 and 1")
        if self.valid_from is not None:
            require_aware(self.valid_from, "valid_from")
        if self.valid_until is not None:
            require_aware(self.valid_until, "valid_until")
        if self.valid_from and self.valid_until and self.valid_until <= self.valid_from:
            raise ValidationError("valid_until must be after valid_from")

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        for key in ("observed_at", "recorded_at", "valid_from", "valid_until"):
            value = payload[key]
            payload[key] = value.isoformat() if value else None
        payload["source_type"] = self.source_type.value
        payload["confirmation_status"] = self.confirmation_status.value
        payload["sensitivity"] = self.sensitivity.value
        return payload

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> Provenance:
        def parse_optional(value: str | None) -> datetime | None:
            return datetime.fromisoformat(value) if value else None

        return cls(
            source_type=SourceType(payload["source_type"]),
            source_identifier=str(payload["source_identifier"]),
            observed_at=datetime.fromisoformat(payload["observed_at"]),
            recorded_at=datetime.fromisoformat(payload["recorded_at"]),
            confidence=float(payload["confidence"]),
            confirmation_status=ConfirmationStatus(payload["confirmation_status"]),
            sensitivity=Sensitivity(payload["sensitivity"]),
            actor_id=str(payload["actor_id"]),
            data_subject_id=str(payload["data_subject_id"]),
            controller_id=str(payload["controller_id"]),
            correlation_id=str(payload["correlation_id"]),
            valid_from=parse_optional(payload.get("valid_from")),
            valid_until=parse_optional(payload.get("valid_until")),
            input_references=tuple(str(value) for value in payload.get("input_references", ())),
            supersedes_reference=(
                str(payload["supersedes_reference"])
                if payload.get("supersedes_reference") is not None
                else None
            ),
        )
