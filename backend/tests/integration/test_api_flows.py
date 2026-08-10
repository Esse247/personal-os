from __future__ import annotations

from typing import Any

from fastapi.testclient import TestClient

from personal_os.fixtures import OTHER_TRANSACTION_ID, TRANSACTION_ID

HAIRCUT_TEXT = "I need a haircut before the wedding next month."


def capture(client: TestClient, key: str, text: str = HAIRCUT_TEXT) -> dict[str, Any]:
    response = client.post(
        "/v1/intents",
        headers={"Idempotency-Key": key},
        json={"text": text},
    )
    assert response.status_code == 201, response.text
    assert response.headers["cache-control"] == "no-store"
    return response.json()


def decide(
    client: TestClient,
    proposal: dict[str, Any],
    action: str,
    key: str,
) -> dict[str, Any]:
    response = client.post(
        f"/v1/schedule-proposals/{proposal['id']}/decisions",
        headers={
            "Idempotency-Key": key,
            "If-Match": f'"{proposal["version"]}"',
        },
        json={"decision": action},
    )
    assert response.status_code == 200, response.text
    return response.json()


def test_required_flow_a_change_approve_and_audit(client: TestClient) -> None:
    result = capture(client, "flow-a-capture-0001")
    intent = result["intent"]
    commitment = result["commitment"]
    proposal = result["proposal"]
    assert isinstance(intent, dict) and intent["status"] == "committed"
    assert intent["provenance"]["source_type"] == "USER_STATED"
    assert isinstance(commitment, dict) and commitment["status"] == "captured"
    assert isinstance(proposal, dict) and proposal["status"] == "proposed"

    changed = decide(client, proposal, "change", "flow-a-change-0001")
    replacement = changed["replacement"]
    assert isinstance(replacement, dict)
    assert changed["proposal"]["status"] == "superseded"
    assert replacement["revision"] == 2
    assert replacement["starts_at"] != proposal["starts_at"]

    approved = decide(client, replacement, "approve", "flow-a-approve-0001")
    assert approved["proposal"]["status"] == "approved"
    assert approved["commitment"]["status"] == "scheduled"

    dashboard = client.get("/v1/dashboard").json()
    assert len(dashboard["schedule"]) == 1
    actions = {event["action"] for event in dashboard["activity"]}
    assert {
        "intent.captured",
        "commitment.created",
        "schedule.proposed",
        "schedule.changed",
        "schedule.approved",
    } <= actions


def test_reject_keeps_commitment_actionable(client: TestClient) -> None:
    proposal = capture(client, "flow-a-reject-capture-0001")["proposal"]
    assert isinstance(proposal, dict)
    rejected = decide(client, proposal, "reject", "flow-a-reject-0001")
    assert rejected["proposal"]["status"] == "rejected"
    assert rejected["commitment"]["status"] == "waiting"
    assert "rejected" in rejected["commitment"]["waiting_reason"].casefold()


def test_stale_proposal_decision_fails_without_second_block(client: TestClient) -> None:
    proposal = capture(client, "stale-capture-0001")["proposal"]
    assert isinstance(proposal, dict)
    decide(client, proposal, "approve", "stale-approve-0001")
    replay = client.post(
        f"/v1/schedule-proposals/{proposal['id']}/decisions",
        headers={"Idempotency-Key": "different-replay-key", "If-Match": '"1"'},
        json={"decision": "approve"},
    )
    assert replay.status_code == 409
    assert len(client.get("/v1/dashboard").json()["schedule"]) == 1


def test_approval_idempotency_key_creates_exactly_one_block(client: TestClient) -> None:
    proposal = capture(client, "idempotent-capture-0001")["proposal"]
    assert isinstance(proposal, dict)
    headers = {
        "Idempotency-Key": "idempotent-approval-0001",
        "If-Match": f'"{proposal["version"]}"',
    }
    path = f"/v1/schedule-proposals/{proposal['id']}/decisions"
    first = client.post(path, headers=headers, json={"decision": "approve"})
    second = client.post(path, headers=headers, json={"decision": "approve"})
    assert first.status_code == second.status_code == 200
    dashboard = client.get("/v1/dashboard").json()
    assert len(dashboard["schedule"]) == 1
    assert (
        len([item for item in dashboard["approvals"] if item["proposal_id"] == proposal["id"]]) == 1
    )


def test_capture_idempotency_replays_exact_result_and_rejects_mutation(
    client: TestClient,
) -> None:
    headers = {"Idempotency-Key": "capture-receipt-exact-0001"}
    first = client.post("/v1/intents", headers=headers, json={"text": HAIRCUT_TEXT})
    second = client.post("/v1/intents", headers=headers, json={"text": HAIRCUT_TEXT})
    assert first.status_code == second.status_code == 201
    assert first.json() == second.json()
    dashboard = client.get("/v1/dashboard").json()
    assert len(dashboard["commitments"]) == 1
    assert len(dashboard["proposals"]) == 1
    assert (
        len([event for event in dashboard["activity"] if event["action"] == "intent.captured"]) == 1
    )

    mutated = client.post(
        "/v1/intents",
        headers=headers,
        json={"text": "Book something next month"},
    )
    assert mutated.status_code == 409
    assert len(client.get("/v1/dashboard").json()["commitments"]) == 1
    denied = client.get("/v1/audit-events").json()
    assert any(event["action"] == "command.idempotency_reuse_denied" for event in denied)


def test_decision_receipt_rejects_changed_payload_and_replays_change(
    client: TestClient,
) -> None:
    proposal = capture(client, "decision-receipt-capture-0001")["proposal"]
    assert isinstance(proposal, dict)
    path = f"/v1/schedule-proposals/{proposal['id']}/decisions"
    headers = {
        "Idempotency-Key": "decision-receipt-change-0001",
        "If-Match": f'"{proposal["version"]}"',
    }
    first = client.post(path, headers=headers, json={"decision": "change"})
    second = client.post(path, headers=headers, json={"decision": "change"})
    assert first.status_code == second.status_code == 200
    assert first.json() == second.json()
    replacement_id = first.json()["replacement"]["id"]
    dashboard = client.get("/v1/dashboard").json()
    assert len([item for item in dashboard["proposals"] if item["id"] == replacement_id]) == 1
    assert (
        len([item for item in dashboard["approvals"] if item["proposal_id"] == proposal["id"]]) == 1
    )

    mutated = client.post(path, headers=headers, json={"decision": "reject"})
    assert mutated.status_code == 409


def test_confirmed_blocks_are_hard_constraints_for_later_planning(
    client: TestClient,
) -> None:
    first = capture(client, "conflict-first-capture-0001")["proposal"]
    assert isinstance(first, dict)
    decide(client, first, "approve", "conflict-first-approve-0001")

    second = capture(client, "conflict-second-capture-0001")["proposal"]
    assert isinstance(second, dict)
    assert second["starts_at"] != first["starts_at"]
    decide(client, second, "approve", "conflict-second-approve-0001")
    blocks = client.get("/v1/dashboard").json()["schedule"]
    assert len(blocks) == 2
    assert blocks[0]["ends_at"] <= blocks[1]["starts_at"]


def test_derived_records_and_audit_keep_typed_provenance(client: TestClient) -> None:
    result = capture(client, "provenance-capture-0001")
    assert result["commitment"]["provenance"]["source_type"] == "SYSTEM_INFERRED"
    assert len(result["commitment"]["provenance"]["input_references"]) == 4
    assert result["proposal"]["provenance"]["source_type"] == "SYSTEM_INFERRED"
    proposed = next(
        event
        for event in client.get("/v1/audit-events").json()
        if event["action"] == "schedule.proposed"
    )
    assert proposed["source_type"] == "SYSTEM_INFERRED"
    assert proposed["actor_id"] == "chief-of-staff-system"
    assert proposed["entity_version"] == 1
    assert proposed["causation_id"] == "provenance-capture-0001"
    assert proposed["policy_result"].startswith("allowed:")
    assert proposed["capability_mode"] == "local-mock-synthetic"


def test_ambiguous_input_requires_clarification_without_inventing_state(
    client: TestClient,
) -> None:
    result = capture(client, "ambiguous-capture-0001", "Book something next month")
    assert result["intent"]["status"] == "needs_clarification"
    assert result["intent"]["due_at"] is None
    assert result["commitment"] is None
    assert result["proposal"] is None


def test_required_flow_b_preserves_source_confidence_and_audit(client: TestClient) -> None:
    response = client.get(f"/v1/finance/transactions/{TRANSACTION_ID}")
    assert response.status_code == 200
    transaction = response.json()
    assert transaction["amount_minor"] == -245000
    assert transaction["currency"] == "GBP"
    assert transaction["source"]["source_type"] == "TOOL_OBSERVED"
    assert transaction["source"]["source_identifier"] == "synthetic-bank-transaction-001"
    assert transaction["classification"]["rule_id"] == "house-materials-keyword-v1"
    assert transaction["classification"]["confidence"] == 0.98
    actions = {event["action"] for event in client.get("/v1/audit-events").json()}
    assert "finance.transaction_imported" in actions
    assert "finance.transaction_categorised" in actions


def test_household_membership_does_not_expose_other_person_data(client: TestClient) -> None:
    listed = client.get("/v1/finance/transactions").json()
    assert {transaction["id"] for transaction in listed} == {TRANSACTION_ID}
    denied = client.get(f"/v1/finance/transactions/{OTHER_TRANSACTION_ID}")
    assert denied.status_code == 404
    assert "other-user" not in denied.text
    audit = client.get("/v1/audit-events").json()
    denial = next(event for event in audit if event["action"] == "authorization.denied")
    assert denial["entity_id"] == "protected-resource"


def test_capability_and_status_surfaces_cannot_claim_live(client: TestClient) -> None:
    capabilities = client.get("/v1/system/capabilities").json()
    assert capabilities["phase"] == "foundation-v0.1"
    assert capabilities["live_capabilities"] == []
    assert all(item["status"] != "live" for item in capabilities["capabilities"].values())
    status = client.get("/v1/system/status").json()
    assert status == {
        "environment": "LOCAL",
        "provider_mode": "MOCK",
        "data_mode": "SYNTHETIC",
        "identity_mode": "DEVELOPMENT PERSONA",
        "external_actions": "PROHIBITED",
    }


def test_one_normalized_correlation_id_links_response_logical_command_and_audit(
    client: TestClient,
) -> None:
    response = client.post(
        "/v1/intents",
        headers={"Idempotency-Key": "correlation-generated-0001"},
        json={"text": "Book something next month"},
    )
    assert response.status_code == 201
    correlation_id = response.headers["x-correlation-id"]
    audit = client.get("/v1/audit-events").json()
    captured = next(event for event in audit if event["action"] == "intent.captured")
    assert captured["correlation_id"] == correlation_id

    invalid = client.post(
        "/v1/intents",
        headers={
            "Idempotency-Key": "correlation-invalid-0001",
            "X-Correlation-ID": "x" * 65,
        },
        json={"text": "Book something next month"},
    )
    assert invalid.status_code == 201
    normalized = invalid.headers["x-correlation-id"]
    assert normalized != "x" * 65
    invalid_intent_id = invalid.json()["intent"]["id"]
    invalid_audit = client.get("/v1/audit-events").json()
    invalid_capture = next(
        event
        for event in invalid_audit
        if event["action"] == "intent.captured" and event["entity_id"] == invalid_intent_id
    )
    assert invalid_capture["correlation_id"] == normalized
