import { render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import App from "./App";
import type { Dashboard } from "./types";

const fixture: Dashboard = {
  mode: { environment: "LOCAL", providers: "MOCK", data: "SYNTHETIC" },
  now: { headline: "Choose deliberately, then leave room", detail: "Buffers remain protected." },
  today: { date: "2026-08-10", scheduled_count: 0, protected_unstructured_minutes: 120 },
  primary_project: { id: "p1", name: "Lantern House", status: "active" },
  projects: [{ id: "p1", name: "Lantern House", status: "active" }],
  commitments: [],
  proposals: [],
  schedule: [],
  transactions: [{
    id: "t1",
    merchant: "Northstar Timber Yard",
    memo: "<img src=x onerror=alert('unsafe')> Synthetic fixture",
    amount_minor: -245000,
    currency: "GBP",
    posted_at: "2026-08-08T10:20:00+00:00",
    project_id: "p1",
    source_type: "TOOL_OBSERVED",
    source_identifier: "synthetic-1",
    confidence: 1,
    category: "House project · materials",
    category_confidence: 0.98,
    category_rule: "house-materials-keyword-v1"
  }],
  approvals: [],
  activity: [],
  system_status: { api: "implemented", external_actions: "prohibited" }
};

describe("PERSONAL OS dashboard", () => {
  afterEach(() => vi.restoreAllMocks());

  it("renders every required foundation region with truthful mode labels", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue({ ok: true, json: async () => fixture }));
    render(<App />);
    expect(await screen.findByText("Choose deliberately, then leave room")).toBeInTheDocument();
    expect(screen.getByText("MOCK PROVIDERS")).toBeInTheDocument();
    expect(screen.getByText("Approval queue")).toBeInTheDocument();
    expect(screen.getByText("Current focus")).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Commitments" })).toBeInTheDocument();
    expect(screen.getByText("Latest transaction")).toBeInTheDocument();
    expect(screen.getByText("Agent & activity")).toBeInTheDocument();
    expect(screen.getByText("System status")).toBeInTheDocument();
    expect(screen.getByLabelText("Capture an intention")).toBeInTheDocument();
    expect(screen.getByText(/<img src=x onerror=/)).toBeInTheDocument();
    expect(document.querySelector("img")).toBeNull();
  });
});
