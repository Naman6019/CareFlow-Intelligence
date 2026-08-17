import Link from "next/link";

import { getApi } from "@/lib/api";

export const dynamic = "force-dynamic";

type Patient = {
  id: string;
  first_name: string;
  middle_name: string | null;
  last_name: string;
  birth_date: string;
  death_date: string | null;
  gender: string | null;
  city: string | null;
  state: string | null;
};

type PatientList = {
  items: Patient[];
  page: number;
  page_size: number;
  total: number;
  pages: number;
  search: string;
};

function patientName(patient: Patient) {
  return [patient.first_name, patient.middle_name, patient.last_name]
    .filter(Boolean)
    .join(" ");
}

function pageHref(page: number, search: string) {
  const params = new URLSearchParams();
  if (search) {
    params.set("search", search);
  }
  params.set("page", String(page));
  return `/patients?${params.toString()}`;
}

export default async function PatientsPage({
  searchParams,
}: {
  searchParams: Promise<{ search?: string; page?: string }>;
}) {
  const params = await searchParams;
  const search = params.search?.trim() ?? "";
  const requestedPage = Number.parseInt(params.page ?? "1", 10);
  const page = Number.isFinite(requestedPage) && requestedPage > 0
    ? requestedPage
    : 1;
  const query = new URLSearchParams({
    search,
    page: String(page),
    page_size: "20",
  });
  const data = await getApi<PatientList>(`/api/patients?${query.toString()}`);

  return (
    <>
      <header className="page-header">
        <div>
          <p className="eyebrow">Patient explorer</p>
          <h1>Synthetic patients</h1>
          <p>
            Search imported records and open a unified clinical timeline.
          </p>
        </div>
        <div className="count-badge">{data.total} records</div>
      </header>

      <form className="patient-search" method="get">
        <label htmlFor="patient-search">Search patients</label>
        <div>
          <input
            defaultValue={search}
            id="patient-search"
            name="search"
            placeholder="Name, city, state, or patient ID"
            type="search"
          />
          <button type="submit">Search</button>
        </div>
      </form>

      {data.items.length ? (
        <section className="patient-list" aria-label="Patient results">
          <div className="patient-list-header">
            <span>Patient</span>
            <span>Birth date</span>
            <span>Location</span>
            <span />
          </div>
          {data.items.map((patient) => (
            <article className="patient-row" key={patient.id}>
              <div>
                <strong>{patientName(patient)}</strong>
                <span>{patient.gender ?? "Unknown gender"}</span>
              </div>
              <time dateTime={patient.birth_date}>{patient.birth_date}</time>
              <span>
                {[patient.city, patient.state].filter(Boolean).join(", ") ||
                  "Location unavailable"}
              </span>
              <Link href={`/patients/${patient.id}`}>View timeline</Link>
            </article>
          ))}
        </section>
      ) : (
        <section className="empty-state">
          <h2>No patients found</h2>
          <p>Try a different name, city, state, or patient identifier.</p>
        </section>
      )}

      {data.pages > 1 && (
        <nav className="pagination" aria-label="Patient pages">
          {data.page > 1 ? (
            <Link href={pageHref(data.page - 1, search)}>Previous</Link>
          ) : (
            <span />
          )}
          <span>
            Page {data.page} of {data.pages}
          </span>
          {data.page < data.pages ? (
            <Link href={pageHref(data.page + 1, search)}>Next</Link>
          ) : (
            <span />
          )}
        </nav>
      )}
    </>
  );
}

