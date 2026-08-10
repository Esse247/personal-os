from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from personal_os.domain.errors import ValidationError


class ActionLevel(StrEnum):
    LEVEL_0 = "observe_read"
    LEVEL_1 = "analyse_suggest"
    LEVEL_2 = "draft_simulate"
    LEVEL_3 = "reversible_internal_write"
    LEVEL_4 = "external_side_effect"
    LEVEL_5 = "high_risk_or_irreversible"
    PROHIBITED = "prohibited"


@dataclass(frozen=True, slots=True)
class ToolActionDeclaration:
    permission: str
    action_level: ActionLevel
    allowed_environment: str
    input_sensitivity: str
    output_sensitivity: str
    reversible: bool
    idempotency_behavior: str
    required_approval: str
    expected_evidence: str
    retry_policy: str
    recovery_path: str
    data_recipient: str
    disclosure_purpose: str

    def __post_init__(self) -> None:
        required_text = {
            "permission": self.permission,
            "allowed_environment": self.allowed_environment,
            "input_sensitivity": self.input_sensitivity,
            "output_sensitivity": self.output_sensitivity,
            "idempotency_behavior": self.idempotency_behavior,
            "required_approval": self.required_approval,
            "expected_evidence": self.expected_evidence,
            "retry_policy": self.retry_policy,
            "recovery_path": self.recovery_path,
            "data_recipient": self.data_recipient,
            "disclosure_purpose": self.disclosure_purpose,
        }
        missing = [name for name, value in required_text.items() if not value.strip()]
        if missing:
            raise ValidationError(f"tool action declaration is missing: {', '.join(missing)}")
