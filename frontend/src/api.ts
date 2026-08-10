import type { CaptureResult, Dashboard, DecisionResult, Proposal } from "./types";

async function parseResponse<T>(response: Response): Promise<T> {
  if (!response.ok) {
    const problem = (await response.json().catch(() => null)) as { detail?: string } | null;
    throw new Error(problem?.detail ?? `Request failed with status ${response.status}`);
  }
  return (await response.json()) as T;
}

export async function loadDashboard(): Promise<Dashboard> {
  return parseResponse<Dashboard>(await fetch("/v1/dashboard", { cache: "no-store" }));
}

export async function captureIntent(text: string): Promise<CaptureResult> {
  return parseResponse<CaptureResult>(
    await fetch("/v1/intents", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "Idempotency-Key": crypto.randomUUID()
      },
      body: JSON.stringify({ text })
    })
  );
}

export async function decideProposal(
  proposal: Proposal,
  decision: "approve" | "change" | "reject"
): Promise<DecisionResult> {
  return parseResponse<DecisionResult>(
    await fetch(`/v1/schedule-proposals/${proposal.id}/decisions`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "Idempotency-Key": crypto.randomUUID(),
        "If-Match": `"${proposal.version}"`
      },
      body: JSON.stringify({ decision })
    })
  );
}
