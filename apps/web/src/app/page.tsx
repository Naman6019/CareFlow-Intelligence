"use client";

import { useEffect, useState } from "react";

type ApiState = "checking" | "online" | "offline";

const buildSteps = [
  {
    title: "Synthetic patient data",
    description: "Import a reproducible Synthea dataset into PostgreSQL.",
  },
  {
    title: "Patient timeline",
    description: "Browse encounters, conditions, medications, and observations.",
  },
  {
    title: "Grounded AI agent",
    description: "Upload documents, ask cited questions, and review suggested actions.",
  },
];

export default function Home() {
  const [apiState, setApiState] = useState<ApiState>("checking");

  useEffect(() => {
    const apiUrl =
      process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

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
        <span className="phase">Foundation · Step 1</span>
      </nav>

      <section className="hero">
        <div>
          <p className="eyebrow">Healthcare operations sandbox</p>
          <h1>Understand the patient journey.</h1>
          <p className="intro">
            A human-reviewed workspace for exploring synthetic patient timelines,
            documents, care operations, and grounded AI assistance.
          </p>
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
            The first milestone verifies the web, API, and database foundation
            before patient imports or AI features are introduced.
          </p>
        </aside>
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

