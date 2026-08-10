from __future__ import annotations

from typing import Final

CAPABILITIES: Final[dict[str, dict[str, str]]] = {
    "project_memory": {"status": "implemented", "mode": "local"},
    "intent_capture": {"status": "implemented", "mode": "synthetic"},
    "clarification": {"status": "implemented", "mode": "deterministic"},
    "commitment_tracking": {"status": "implemented", "mode": "local"},
    "deterministic_scheduling": {"status": "implemented", "mode": "local"},
    "calendar_availability": {"status": "mocked", "mode": "mock"},
    "calendar_external_write": {"status": "prohibited", "mode": "none"},
    "schedule_approval": {"status": "implemented", "mode": "internal_reversible"},
    "finance_transaction_import": {"status": "mocked", "mode": "synthetic"},
    "finance_categorisation": {"status": "implemented", "mode": "deterministic"},
    "banking_live_read": {"status": "prohibited", "mode": "none"},
    "payment_or_transfer": {"status": "prohibited", "mode": "none"},
    "dashboard": {"status": "implemented", "mode": "local"},
    "audit_history": {"status": "implemented", "mode": "local_append_only"},
    "agent_activity": {"status": "planned", "mode": "synthetic"},
    "external_notifications": {"status": "prohibited", "mode": "none"},
    "production_authentication": {"status": "planned", "mode": "future"},
    "model_inference": {"status": "mocked", "mode": "deterministic_mock_contract"},
    "health_guidance": {"status": "prohibited", "mode": "none"},
}
