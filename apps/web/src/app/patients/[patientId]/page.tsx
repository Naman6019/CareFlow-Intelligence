import Link from "next/link";
import { notFound } from "next/navigation";

import { ApiError, getApi } from "@/lib/api";

export const dynamic = "force-dynamic";

type PatientDetail = {
  id: string;
  first_name: string;
  middle_name: string | null;
  last_name: string;
  birth_date: string;
  death_date: string | null;
  gender: string | null;
  race: string | null;
  ethnicity: string | null;
  city: string | null;
  state: string | null;
  postal_code: string | null;
  stats: Record<"encounters" | "conditions" | "observations" | "medications", number>;
};

type TimelineEvent = {
  id: string;
  event_type: "encounter" | "condition" | "observation" | "medication";
  occurred_at: string;
  ended_at: string | null;
  category: string | null;
  code: string | null;
  title: string;
  description: string | null;
  value: string | null;
  units: string | null;
};

type Timeline = {
  patient_id: string;
  events: TimelineEvent[];
  returned: number;
  limit: number;
};

function displayDate(value: string) {
  return new Intl.DateTimeFormat("en", {
    dateStyle: "medium",
    timeStyle: value.includes("T") ? "short" : undefined,
    timeZone: "UTC",
  }).format(new Date(value));
}

function patientName(patient: PatientDetail) {
  return [patient.first_name, patient.middle_name, patient.last_name]
    .filter(Boolean)
    .join(" ");
}

export default async function PatientTimelinePage({
  params,
}: {
  params: Promise<{ patientId: string }>;
}) {
  const { patientId } = await params;

  try {
    const [patient, timeline] = await Promise.all([
      getApi<PatientDetail>(`/api/patients/${patientId}`),
      getApi<Timeline>(`/api/patients/${patientId}/timeline?limit=300`),
    ]);

    return (
      <>
        <Link className="back-link" href="/patients">
          ← Back to patients
        </Link>

        <header className="patient-profile">
          <div>
            <p className="eyebrow">Synthetic patient timeline</p>
            <h1>{patientName(patient)}</h1>
            <p>
              Born {displayDate(patient.birth_date)} ·{" "}
              {[patient.city, patient.state].filter(Boolean).join(", ") ||
                "Location unavailable"}
            </p>
            <code>{patient.id}</code>
          </div>
          <div className="patient-demographics">
            <span>{patient.gender ?? "Unknown gender"}</span>
            <span>{patient.race ?? "Unknown race"}</span>
            <span>{patient.ethnicity ?? "Unknown ethnicity"}</span>
          </div>
        </header>

        <section className="stat-grid" aria-label="Patient record counts">
          {Object.entries(patient.stats).map(([label, count]) => (
            <article key={label}>
              <strong>{count.toLocaleString()}</strong>
              <span>{label}</span>
            </article>
          ))}
        </section>

        <section className="timeline-section">
          <div className="timeline-heading">
            <div>
              <p className="eyebrow">Most recent first</p>
              <h2>Clinical timeline</h2>
            </div>
            <span>Showing {timeline.returned} events</span>
          </div>

          <div className="timeline">
            {timeline.events.map((event) => (
              <article
                className={`timeline-event event-${event.event_type}`}
                key={`${event.event_type}-${event.id}`}
              >
                <div className="timeline-marker" aria-hidden="true" />
                <div className="timeline-date">
                  <time dateTime={event.occurred_at}>
                    {displayDate(event.occurred_at)}
                  </time>
                  <span>{event.event_type}</span>
                </div>
                <div className="timeline-card">
                  <div>
                    <h3>{event.title}</h3>
                    {event.category && <span>{event.category}</span>}
                  </div>
                  {event.value && (
                    <strong className="event-value">
                      {event.value} {event.units}
                    </strong>
                  )}
                  {event.description && <p>{event.description}</p>}
                  {event.code && <code>Code {event.code}</code>}
                </div>
              </article>
            ))}
          </div>
        </section>
      </>
    );
  } catch (error) {
    if (error instanceof ApiError && error.status === 404) {
      notFound();
    }
    throw error;
  }
}

