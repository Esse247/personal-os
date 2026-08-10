from __future__ import annotations

import json

from fastapi.testclient import TestClient

from personal_os.adapters.persistence.database import create_database_engine
from personal_os.config import Settings
from personal_os.fixtures import TRANSACTION_ID
from personal_os.interfaces.http.app import create_app


def decision_headers(version: int, key: str) -> dict[str, str]:
    return {"Idempotency-Key": key, "If-Match": f'"{version}"'}


def run_demo() -> dict[str, object]:
    engine = create_database_engine("sqlite+pysqlite:///:memory:")
    settings = Settings(database_url="sqlite+pysqlite:///:memory:")
    application = create_app(settings=settings, engine=engine)

    with TestClient(application) as client:
        first = client.post(
            "/v1/intents",
            headers={"Idempotency-Key": "demo-haircut-capture-001"},
            json={"text": "I need a haircut before the wedding next month."},
        )
        first.raise_for_status()
        captured = first.json()
        assert captured["intent"]["status"] == "committed"
        assert captured["commitment"]["status"] == "captured"
        proposal = captured["proposal"]

        changed_response = client.post(
            f"/v1/schedule-proposals/{proposal['id']}/decisions",
            headers=decision_headers(proposal["version"], "demo-change-decision-001"),
            json={"decision": "change"},
        )
        changed_response.raise_for_status()
        replacement = changed_response.json()["replacement"]
        assert replacement["revision"] == 2

        approved_response = client.post(
            f"/v1/schedule-proposals/{replacement['id']}/decisions",
            headers=decision_headers(replacement["version"], "demo-approve-decision-001"),
            json={"decision": "approve"},
        )
        approved_response.raise_for_status()
        approved = approved_response.json()
        assert approved["commitment"]["status"] == "scheduled"

        second = client.post(
            "/v1/intents",
            headers={"Idempotency-Key": "demo-haircut-capture-002"},
            json={"text": "I need a haircut before the wedding next month."},
        )
        second.raise_for_status()
        rejected_proposal = second.json()["proposal"]
        rejected_response = client.post(
            f"/v1/schedule-proposals/{rejected_proposal['id']}/decisions",
            headers=decision_headers(rejected_proposal["version"], "demo-reject-decision-001"),
            json={"decision": "reject"},
        )
        rejected_response.raise_for_status()
        assert rejected_response.json()["commitment"]["status"] == "waiting"

        ambiguous_response = client.post(
            "/v1/intents",
            headers={"Idempotency-Key": "demo-ambiguous-capture-001"},
            json={"text": "Book something next month"},
        )
        ambiguous_response.raise_for_status()
        ambiguous = ambiguous_response.json()
        assert ambiguous["intent"]["status"] == "needs_clarification"
        assert ambiguous["commitment"] is None and ambiguous["proposal"] is None

        finance_response = client.get(f"/v1/finance/transactions/{TRANSACTION_ID}")
        finance_response.raise_for_status()
        finance = finance_response.json()
        assert finance["classification"]["rule_id"] == "house-materials-keyword-v1"

        dashboard_response = client.get("/v1/dashboard")
        dashboard_response.raise_for_status()
        dashboard = dashboard_response.json()
        audit_actions = {item["action"] for item in dashboard["activity"]}
        required_actions = {
            "intent.captured",
            "commitment.created",
            "schedule.proposed",
            "schedule.changed",
            "schedule.approved",
            "schedule.rejected",
            "intent.clarification_requested",
            "finance.transaction_categorised",
        }
        assert required_actions <= audit_actions

        capabilities = client.get("/v1/system/capabilities").json()
        assert capabilities["live_capabilities"] == []

        frontend = client.get("/")
        assert frontend.status_code == 200
        assert "PERSONAL OS" in frontend.text

        return {
            "mode": "local-mock-synthetic",
            "flow_a": {
                "intent": captured["intent"]["status"],
                "proposal_revisions": [proposal["revision"], replacement["revision"]],
                "approved_commitment": approved["commitment"]["status"],
                "rejected_commitment": rejected_response.json()["commitment"]["status"],
                "audit_actions_verified": sorted(required_actions),
            },
            "ambiguous_input": ambiguous["intent"]["status"],
            "flow_b": {
                "transaction": finance["id"],
                "category": finance["classification"]["category"],
                "confidence": finance["classification"]["confidence"],
                "source_type": finance["source"]["source_type"],
            },
            "frontend": "built dashboard served locally",
            "live_capabilities": [],
        }


def main() -> None:
    print(json.dumps(run_demo(), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
