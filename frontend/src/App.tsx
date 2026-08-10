import { FormEvent, useCallback, useEffect, useMemo, useState } from "react";
import { captureIntent, decideProposal, loadDashboard } from "./api";
import type { CaptureResult, Dashboard, Proposal, Transaction } from "./types";

const DEFAULT_CAPTURE = "I need a haircut before the wedding next month.";

function shortDate(value: string): string {
  return new Intl.DateTimeFormat("en-GB", {
    weekday: "short",
    day: "numeric",
    month: "short",
    hour: "2-digit",
    minute: "2-digit",
    timeZone: "UTC"
  }).format(new Date(value));
}

function money(transaction: Transaction): string {
  return new Intl.NumberFormat("en-GB", {
    style: "currency",
    currency: transaction.currency
  }).format(transaction.amount_minor / 100);
}

function SectionTitle({ eyebrow, title }: { eyebrow: string; title: string }) {
  return (
    <div className="section-title">
      <span>{eyebrow}</span>
      <h2>{title}</h2>
    </div>
  );
}

function StatusPill({ children, tone = "neutral" }: { children: React.ReactNode; tone?: string }) {
  return <span className={`pill pill-${tone}`}>{children}</span>;
}

export default function App() {
  const [dashboard, setDashboard] = useState<Dashboard | null>(null);
  const [capture, setCapture] = useState(DEFAULT_CAPTURE);
  const [notice, setNotice] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const refresh = useCallback(async () => {
    const value = await loadDashboard();
    setDashboard(value);
  }, []);

  useEffect(() => {
    refresh().catch((reason: unknown) => {
      setError(reason instanceof Error ? reason.message : "Dashboard unavailable");
    });
  }, [refresh]);

  const pending = useMemo(
    () => dashboard?.proposals.filter((proposal) => proposal.status === "proposed") ?? [],
    [dashboard]
  );

  async function submitCapture(event: FormEvent) {
    event.preventDefault();
    if (!capture.trim()) return;
    setBusy(true);
    setError(null);
    setNotice(null);
    try {
      const result: CaptureResult = await captureIntent(capture.trim());
      if (result.intent.status === "needs_clarification") {
        setNotice(result.intent.clarification_question ?? "I need one more detail.");
      } else {
        setNotice("Intent structured, commitment recorded, and a mock-calendar proposal prepared.");
      }
      await refresh();
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Capture failed");
    } finally {
      setBusy(false);
    }
  }

  async function decide(proposal: Proposal, decision: "approve" | "change" | "reject") {
    setBusy(true);
    setError(null);
    setNotice(null);
    try {
      const result = await decideProposal(proposal, decision);
      if (decision === "approve") {
        setNotice("Approved as a reversible internal block. No external calendar was changed.");
      } else if (decision === "change") {
        setNotice(`Revision ${result.replacement?.revision ?? "next"} recalculated from mock availability.`);
      } else {
        setNotice("Proposal rejected. The commitment remains visible and waiting for a better plan.");
      }
      await refresh();
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Decision failed");
    } finally {
      setBusy(false);
    }
  }

  if (!dashboard) {
    return (
      <main className="loading-shell">
        <div className="brand-mark">P</div>
        <p>{error ?? "Preparing your local foundation…"}</p>
      </main>
    );
  }

  return (
    <div className="app-shell">
      <header className="topbar">
        <div className="brand">
          <div className="brand-mark" aria-hidden="true">P</div>
          <div>
            <strong>PERSONAL OS</strong>
            <span>Foundation v0.1</span>
          </div>
        </div>
        <div className="mode-strip" aria-label="System mode">
          <StatusPill tone="safe">LOCAL</StatusPill>
          <StatusPill tone="warm">MOCK PROVIDERS</StatusPill>
          <StatusPill>SYNTHETIC DATA</StatusPill>
        </div>
      </header>

      <aside className="sidebar" aria-label="Dashboard sections">
        <span className="nav-label">Today</span>
        {['Now', 'Schedule', 'Commitments', 'Projects'].map((item, index) => (
          <a className={index === 0 ? "active" : ""} href={`#${item.toLowerCase()}`} key={item}>
            <span className="nav-dot" aria-hidden="true" />{item}
          </a>
        ))}
        <span className="nav-label">Household</span>
        <a href="#finance"><span className="nav-dot" aria-hidden="true" />House finance</a>
        <span className="nav-label">System</span>
        <a href="#activity"><span className="nav-dot" aria-hidden="true" />Activity</a>
        <a href="#status"><span className="nav-dot" aria-hidden="true" />Status</a>
        <div className="sidebar-note">
          <span>Human authority</span>
          <strong>Always required</strong>
          <p>No external action can run in this foundation.</p>
        </div>
      </aside>

      <main className="dashboard">
        <section className="hero" id="now">
          <div>
            <span className="kicker">MONDAY · 10 AUGUST</span>
            <h1>{dashboard.now.headline}</h1>
            <p>{dashboard.now.detail}</p>
          </div>
          <div className="space-meter" aria-label="Protected unstructured time">
            <span>Open space</span>
            <strong>{dashboard.today.protected_unstructured_minutes}</strong>
            <small>minutes protected today</small>
          </div>
        </section>

        {(notice || error) && (
          <div className={`notice ${error ? "notice-error" : ""}`} role="status">
            <strong>{error ? "Couldn’t complete that" : "Recorded"}</strong>
            <span>{error ?? notice}</span>
          </div>
        )}

        <section className="capture-card" aria-labelledby="capture-title">
          <div className="capture-copy">
            <span className="signal" aria-hidden="true" />
            <div>
              <h2 id="capture-title">What needs your attention?</h2>
              <p>Say it naturally. Missing facts become questions, never guesses.</p>
            </div>
          </div>
          <form onSubmit={submitCapture}>
            <label className="sr-only" htmlFor="capture-input">Capture an intention</label>
            <textarea
              id="capture-input"
              value={capture}
              onChange={(event) => setCapture(event.target.value)}
              rows={2}
              maxLength={2000}
            />
            <button className="primary-button" disabled={busy} type="submit">
              {busy ? "Working…" : "Capture intention"}
            </button>
          </form>
          <div className="capture-foot">
            <button type="button" onClick={() => setCapture("Book something next month")}>Try ambiguous input</button>
            <span>USER-STATED · PRIVATE · AUDITED</span>
          </div>
        </section>

        <div className="dashboard-grid">
          <section className="panel approvals-panel" id="schedule">
            <SectionTitle eyebrow="YOUR DECISION" title="Approval queue" />
            {pending.length === 0 ? (
              <div className="empty-state">
                <span>✓</span>
                <h3>Nothing waiting</h3>
                <p>Capture the haircut intention to create a scheduling proposal.</p>
              </div>
            ) : pending.map((proposal) => (
              <article className="proposal" key={proposal.id}>
                <div className="proposal-head">
                  <div className="date-tile">
                    <strong>{new Date(proposal.starts_at).getUTCDate()}</strong>
                    <span>SEP</span>
                  </div>
                  <div>
                    <span className="eyebrow">SCHEDULE PROPOSAL · REV {proposal.revision}</span>
                    <h3>{shortDate(proposal.starts_at)}</h3>
                    <p>{proposal.rationale}</p>
                  </div>
                </div>
                <div className="proposal-actions">
                  <button className="primary-button" disabled={busy} onClick={() => decide(proposal, "approve")}>Approve block</button>
                  <button disabled={busy} onClick={() => decide(proposal, "change")}>Find another</button>
                  <button className="quiet-button" disabled={busy} onClick={() => decide(proposal, "reject")}>Reject</button>
                </div>
                <p className="boundary-note">Creates an internal block only · no live calendar write</p>
              </article>
            ))}
          </section>

          <section className="panel" id="projects">
            <SectionTitle eyebrow="PRIMARY PROJECT" title="Current focus" />
            <div className="project-card">
              <div className="project-orbit" aria-hidden="true"><span /></div>
              <div>
                <StatusPill tone="safe">{dashboard.primary_project?.status ?? "quiet"}</StatusPill>
                <h3>{dashboard.primary_project?.name ?? "No primary project"}</h3>
                <p>House-project finance is synthetic and isolated to this development persona.</p>
              </div>
            </div>
            <div className="mini-metrics">
              <div><strong>{dashboard.commitments.length}</strong><span>commitments</span></div>
              <div><strong>{dashboard.schedule.length}</strong><span>blocks</span></div>
              <div><strong>{dashboard.projects.length}</strong><span>projects</span></div>
            </div>
          </section>

          <section className="panel" id="commitments">
            <SectionTitle eyebrow="PROMISES KEPT VISIBLE" title="Commitments" />
            <div className="list-stack">
              {dashboard.commitments.length === 0 ? (
                <p className="muted">No captured commitments yet.</p>
              ) : dashboard.commitments.map((commitment) => (
                <article className="list-row" key={commitment.id}>
                  <span className={`state-dot state-${commitment.status}`} aria-hidden="true" />
                  <div>
                    <strong>{commitment.title}</strong>
                    <span>Due {shortDate(commitment.due_at)} · {commitment.duration_minutes} min</span>
                  </div>
                  <StatusPill tone={commitment.status === "scheduled" ? "safe" : "warm"}>
                    {commitment.status.replaceAll("_", " ")}
                  </StatusPill>
                </article>
              ))}
            </div>
          </section>

          <section className="panel finance-panel" id="finance">
            <SectionTitle eyebrow="HOUSE FINANCE · SYNTHETIC" title="Latest transaction" />
            {dashboard.transactions.map((transaction) => (
              <article className="transaction" key={transaction.id}>
                <div className="transaction-top">
                  <div>
                    <span className="eyebrow">{transaction.category}</span>
                    <h3>{transaction.merchant}</h3>
                    <p>{transaction.memo}</p>
                  </div>
                  <strong className="amount">{money(transaction)}</strong>
                </div>
                <div className="provenance-line">
                  <span>{transaction.source_type}</span>
                  <span>{Math.round((transaction.category_confidence ?? 0) * 100)}% category confidence</span>
                  <span>{transaction.category_rule}</span>
                </div>
              </article>
            ))}
          </section>

          <section className="panel activity-panel" id="activity">
            <SectionTitle eyebrow="ATTRIBUTABLE HISTORY" title="Agent & activity" />
            <div className="timeline">
              {dashboard.activity.slice(0, 7).map((event) => (
                <article key={event.id}>
                  <span className="timeline-mark" aria-hidden="true" />
                  <div>
                    <strong>{event.action.replaceAll(".", " · ")}</strong>
                    <p>{event.summary}</p>
                    <small>{event.source_type} · {shortDate(event.occurred_at)}</small>
                  </div>
                </article>
              ))}
            </div>
          </section>

          <section className="panel status-panel" id="status">
            <SectionTitle eyebrow="BOUNDARY CHECK" title="System status" />
            <div className="status-list">
              {Object.entries(dashboard.system_status).map(([name, value]) => (
                <div key={name}>
                  <span>{name.replaceAll("_", " ")}</span>
                  <strong>{value}</strong>
                </div>
              ))}
            </div>
            <p className="system-foot">No credentials loaded · localhost only · external actions prohibited</p>
          </section>
        </div>
      </main>
    </div>
  );
}
