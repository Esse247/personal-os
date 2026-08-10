export type Provenance = {
  source_type: string;
  source_identifier: string;
  observed_at: string;
  recorded_at: string;
  confidence: number;
  confirmation_status: string;
  sensitivity: string;
};

export type Intent = {
  id: string;
  raw_text: string;
  status: string;
  title: string | null;
  due_at: string | null;
  duration_minutes: number | null;
  clarification_question: string | null;
  commitment_id: string | null;
  version: number;
  provenance: Provenance;
};

export type Commitment = {
  id: string;
  title: string;
  status: string;
  due_at: string;
  duration_minutes: number;
  schedule_block_id?: string | null;
  waiting_reason?: string | null;
  review_at?: string | null;
  version: number;
};

export type Proposal = {
  id: string;
  commitment_id: string;
  starts_at: string;
  ends_at: string;
  status: string;
  rationale: string;
  revision: number;
  version: number;
  supersedes_id: string | null;
};

export type Transaction = {
  id: string;
  merchant: string;
  memo: string;
  amount_minor: number;
  currency: string;
  posted_at: string;
  project_id: string | null;
  source_type: string;
  source_identifier: string;
  confidence: number;
  category: string;
  category_confidence: number | null;
  category_rule: string | null;
};

export type Activity = {
  id: string;
  action: string;
  entity_type: string;
  entity_id: string;
  occurred_at: string;
  outcome: string;
  source_type: string;
  summary: string;
  details: Record<string, string | number | boolean | null>;
};

export type Dashboard = {
  mode: Record<string, string>;
  now: { headline: string; detail: string };
  today: {
    date: string;
    scheduled_count: number;
    protected_unstructured_minutes: number;
  };
  primary_project: { id: string; name: string; status: string } | null;
  projects: Array<{ id: string; name: string; status: string }>;
  commitments: Commitment[];
  proposals: Proposal[];
  schedule: Array<{
    id: string;
    commitment_id: string;
    starts_at: string;
    ends_at: string;
    status: string;
  }>;
  transactions: Transaction[];
  approvals: Array<{
    id: string;
    proposal_id: string;
    status: string;
    created_at: string;
  }>;
  activity: Activity[];
  system_status: Record<string, string>;
};

export type CaptureResult = {
  intent: Intent;
  commitment: Commitment | null;
  proposal: Proposal | null;
};

export type DecisionResult = {
  proposal: Proposal;
  replacement: Proposal | null;
  commitment: Commitment;
};
