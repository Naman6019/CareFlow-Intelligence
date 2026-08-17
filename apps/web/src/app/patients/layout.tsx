import Link from "next/link";

export default function PatientsLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <main className="patient-shell">
      <div className="safety-banner">
        Synthetic data only — not for diagnosis, treatment, or clinical use
      </div>
      <nav className="nav patient-nav" aria-label="Patient navigation">
        <Link className="brand brand-link" href="/">
          <span className="brand-mark" aria-hidden="true">
            C
          </span>
          CareFlow Intelligence
        </Link>
        <div className="nav-links">
          <Link className="nav-link" href="/patients">
            Patients
          </Link>
          <Link className="nav-link" href="/assistant">
            Assistant
          </Link>
        </div>
      </nav>
      {children}
    </main>
  );
}
