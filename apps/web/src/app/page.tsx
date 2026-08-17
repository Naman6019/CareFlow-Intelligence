"use client";

import { useEffect, useState } from "react";
import Link from "next/link";

type ApiState = "checking" | "online" | "offline";
type JobStatus =
  | "queued"
  | "downloading"
  | "validating"
  | "awaiting_approval"
  | "approved"
  | "importing"
  | "imported"
  | "failed";

type DataAgentJob = {
  id: string;
  status: JobStatus;
  archive_sha256: string | null;
  archive_size_bytes: number | null;
  error: string | null;
  import_counts: Record<string, number> | null;
  report: {
    patient_count: number;
    row_counts: Record<string, number>;
  } | null;
};

const apiUrl = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
const activeStatuses: JobStatus[] = [
  "queued",
  "downloading",
  "validating",
  "importing",
];

const buildSteps = [
  {
    title: "Data foundation",
    description: "Synthea acquisition, validation, and PostgreSQL import are live.",
  },
  {
    title: "Patient timeline",
    description: "Search patients and browse unified clinical events.",
  },
  {
    title: "Grounded AI agent",
    description: "Upload documents and ask extractive questions with citations.",
  },
];

export default function Home() {
  const [apiState, setApiState] = useState<ApiState>("checking");
  const [job, setJob] = useState<DataAgentJob | null>(null);
  const [agentError, setAgentError] = useState<string | null>(null);

  useEffect(() => {
    fetch(`${apiUrl}/health`)
      .then((response) => {
        if (!response.ok) {
          throw new Error("API health check failed");
        }
        return response.json();
      })
      .then(() => setApiState("online"))
      .catch(() => setApiState("offline"));
  }, []);

  useEffect(() => {
    if (!job || !activeStatuses.includes(job.status)) {
      return;
    }

    const timer = window.setTimeout(async () => {
      const response = await fetch(`${apiUrl}/api/data-agent/jobs/${job.id}`);
      if (response.ok) {
        setJob(await response.json());
      }
    }, 1000);

    return () => window.clearTimeout(timer);
  }, [job]);

  async function startDataAgent() {
    setAgentError(null);
    const response = await fetch(`${apiUrl}/api/data-agent/jobs`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ source_id: "synthea_sample_csv" }),
    });

    if (!response.ok) {
      setAgentError("The data agent could not start.");
      return;
    }

    setJob(await response.json());
  }

  async function approveDataset() {
    if (!job) {
      return;
    }

    const response = await fetch(
      `${apiUrl}/api/data-agent/jobs/${job.id}/approve`,
      { method: "POST" },
    );
    if (!response.ok) {
      setAgentError("The validated dataset could not be approved.");
      return;
    }
    setJob(await response.json());
  }

  async function importDataset() {
    if (!job) {
      return;
    }

    const response = await fetch(
      `${apiUrl}/api/data-agent/jobs/${job.id}/import`,
      { method: "POST" },
    );
    if (!response.ok) {
      setAgentError("The approved dataset could not be imported.");
      return;
    }
    setJob(await response.json());
  }

  const statusText =
    apiState === "checking"
      ? "Checking"
      : apiState === "online"
        ? "Online"
        : "Offline";

  return (
    <main className="shell">
      <div className="safety-banner">
        Synthetic data only — not for diagnosis, treatment, or clinical use
      </div>

      <nav className="nav" aria-label="Primary navigation">
        <div className="brand">
          <span className="brand-mark" aria-hidden="true">
            C
          </span>
          CareFlow Intelligence
        </div>
        <span className="phase">Patient explorer · Step 3</span>
      </nav>

      <section className="hero">
        <div>
          <p className="eyebrow">Healthcare operations sandbox</p>
          <h1>Understand the patient journey.</h1>
          <p className="intro">
            A human-reviewed workspace for exploring synthetic patient timelines,
            documents, care operations, and grounded AI assistance.
          </p>
          <div className="hero-actions">
            <Link className="browse-link" href="/patients">
              Browse patient timelines
            </Link>
            <Link className="assistant-link" href="/assistant">
              Open document assistant
            </Link>
          </div>
        </div>

        <aside className="status-card" aria-live="polite">
          <div className="status-row">
            <div>
              <p className="status-label">FastAPI service</p>
              <p className="status-value">System status</p>
            </div>
            <span
              className={`status-pill ${
                apiState === "online" ? "online" : "offline"
              }`}
            >
              {statusText}
            </span>
          </div>
          <div className="divider" />
          <p className="status-note">
            The web, API, database, synthetic-data import, and patient timeline
            are connected and running.
          </p>
        </aside>
      </section>

      <section className="agent-panel" aria-labelledby="agent-title">
        <div>
          <p className="eyebrow">Controlled data acquisition</p>
          <h2 id="agent-title">Let the agent find and validate the data.</h2>
          <p>
            It downloads only from the approved MITRE Synthea source, validates
            the archive and CSV schemas, and stops for review before PostgreSQL
            import.
          </p>
        </div>

        <div className="agent-actions">
          <button
            className="primary-button"
            disabled={Boolean(job && activeStatuses.includes(job.status))}
            onClick={startDataAgent}
            type="button"
          >
            {job && activeStatuses.includes(job.status)
              ? "Agent working…"
              : "Find Synthea data"}
          </button>

          {job && (
            <div className="agent-result" aria-live="polite">
              <div className="status-row">
                <span>Agent status</span>
                <strong>{job.status.replaceAll("_", " ")}</strong>
              </div>

              {job.report && (
                <>
                  <div className="result-grid">
                    <div>
                      <span>Patients</span>
                      <strong>{job.report.patient_count}</strong>
                    </div>
                    <div>
                      <span>Validated tables</span>
                      <strong>
                        {Object.keys(job.report.row_counts).length}
                      </strong>
                    </div>
                  </div>
                  <p className="checksum">
                    SHA-256: {job.archive_sha256?.slice(0, 18)}…
                  </p>
                </>
              )}

              {job.status === "awaiting_approval" && (
                <button
                  className="approval-button"
                  onClick={approveDataset}
                  type="button"
                >
                  Approve for import
                </button>
              )}

              {job.status === "approved" && (
                <button
                  className="approval-button"
                  onClick={importDataset}
                  type="button"
                >
                  Import into PostgreSQL
                </button>
              )}

              {job.status === "imported" && job.import_counts && (
                <div className="import-summary">
                  {Object.entries(job.import_counts).map(([table, count]) => (
                    <div key={table}>
                      <span>{table}</span>
                      <strong>{count.toLocaleString()}</strong>
                    </div>
                  ))}
                </div>
              )}

              {job.error && <p className="agent-error">{job.error}</p>}
            </div>
          )}

          {agentError && <p className="agent-error">{agentError}</p>}
        </div>
      </section>

      <section className="steps" aria-label="Upcoming build steps">
        {buildSteps.map((step, index) => (
          <article className="step-card" key={step.title}>
            <span className="step-number">{index + 2}</span>
            <h2>{step.title}</h2>
            <p>{step.description}</p>
          </article>
        ))}
      </section>
    </main>
  );
}
