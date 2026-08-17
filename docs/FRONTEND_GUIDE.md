# Frontend & Clinical UI Guide

CareFlow Intelligence features a modern, responsive web application built with **Next.js 15 App Router**, **React 19**, **TypeScript**, and a customized Vanilla CSS design system tailored for clinical readability and operational workflows.

---

## 1. Frontend Architecture & Directory Layout

The frontend codebase is located under `apps/web/`:

```text
apps/web/
├── public/                     # Static assets & icons
├── src/
│   ├── app/
│   │   ├── assistant/          # Grounded Document Assistant & Agent Trace Inspector
│   │   │   └── page.tsx
│   │   ├── patients/           # Patient Explorer & Clinical Timeline
│   │   │   ├── [patientId]/    # Patient Deep-Dive & Longitudinal Event Viewer
│   │   │   │   └── page.tsx
│   │   │   ├── layout.tsx
│   │   │   └── page.tsx
│   │   ├── globals.css         # Global design tokens, typography, and utility classes
│   │   ├── layout.tsx          # Root navigation shell & header bar
│   │   └── page.tsx            # Operations Dashboard & Data Intake Manager
│   └── lib/                    # Shared API client utilities & TypeScript types
├── next.config.ts              # Next.js configuration & API proxy rules
├── package.json
└── tsconfig.json
```

---

## 2. Page Specifications & Clinical Interfaces

### 2.1. Operations Dashboard (`/`)
- **Route**: `http://localhost:3001/`
- **Purpose**: System-level health monitoring and management of the synthetic data intake pipeline.
- **Key Features**:
  - **Live Clinical Metric Counters**: Real-time totals for Patients, Encounters, Conditions, Observations, and Medications fetched from `/api/database/status`.
  - **Data Intake Agent Controller**: One-click triggering of background Synthea sample downloads, live job state polling, and human-in-the-loop approval gates.
  - **Quick Navigation Hub**: Direct shortcuts to the Patient Directory and Document Assistant.

---

### 2.2. Patient Directory (`/patients`)
- **Route**: `http://localhost:3001/patients`
- **Purpose**: Searchable, paginated clinical directory for exploring synthetic patient cohorts.
- **Key Features**:
  - **Instant Search**: Real-time filtering by patient first name, last name, city, state, or UUID.
  - **Demographic Grid**: Cards displaying age, birth date, gender, location, and vital status.
  - **Server-Side Pagination**: Smooth navigation across multi-page cohorts without client lag.

---

### 2.3. Patient Deep Dive & Unified Timeline (`/patients/[patientId]`)
- **Route**: `http://localhost:3001/patients/<patient-uuid>`
- **Purpose**: Comprehensive longitudinal record view for individual patient charts.
- **Key Features**:
  - **Clinical Stats Card**: Aggregates total recorded encounters, active conditions, lab observations, and prescribed medications.
  - **Polymorphic Event Stream**: Color-coded, reverse-chronological timeline unifying:
    - 🔵 **Encounters**: Ambulatory visits, emergency admissions, and wellness checks.
    - 🔴 **Conditions**: SNOMED-CT diagnoses with onset and resolution dates.
    - 🟢 **Observations**: LOINC vitals (Blood Pressure, Heart Rate, BMI) and labs (HbA1c, eGFR, Creatinine, Lipid panels) with units.
    - 🟣 **Medications**: Prescriptions with RxNorm codes and indicated reasons.

---

### 2.4. Grounded Document Assistant (`/assistant`)
- **Route**: `http://localhost:3001/assistant`
- **Purpose**: Interactive clinical literature assistant with verifiable citation provenance and agent execution trace inspectability.
- **Key Features**:
  - **Document Scope Selector**: Filter search context to specific uploaded documents or query the entire clinical knowledge base.
  - **Drag-and-Drop Document Uploader**: Upload PDF guidelines, FDA inserts, markdown notes, or CSV records with immediate server-side chunk indexing.
  - **Verifiable Citation Badges**: Inline citations `[chunk: ID]` rendered as interactive badges that open excerpt sidebars displaying the exact supporting text and relevance rank.
  - **Real-Time Agent Trace Inspector**: Expandable step-by-step trace drawer showing:
    - Tool chosen by the LLM (`list_documents` vs. `search_documents`)
    - Search query reformulation logic
    - Retrieved chunk count and confidence
    - Fallback trigger indicators if the bounded loop was interrupted.

---

## 3. UI Design System & Styling Principles

CareFlow avoids generic UI clichés and implements a purpose-built clinical theme in `apps/web/src/app/globals.css`:

```css
:root {
  --bg-main: #0b132b;          /* Deep slate background */
  --bg-surface: #1c2541;       /* Elevated card background */
  --bg-surface-hover: #243054; /* Interactive hover */
  --border-color: #3a506b;     /* Subtle divider border */
  --text-primary: #f0f4f8;     /* Crisp high-contrast white/slate */
  --text-secondary: #94a3b8;   /* Muted metadata slate */
  --accent-cyan: #48cae4;      /* Clinical action & active status */
  --accent-teal: #00b4d8;      /* Primary button & brand highlight */
  --accent-green: #10b981;     /* Verified ground truth & normal labs */
  --accent-amber: #f59e0b;     /* Warnings & elevated lab values */
  --accent-red: #ef4444;       /* Critical alerts & contraindicated drugs */
}
```

### Design Foundations:
- **Maximum Information Legibility**: High contrast ratios compliant with WCAG 2.2 AA.
- **Zero Decorative Fluff**: Data-dense layouts with clean borders, zero noisy gradients or icon-stuffed bento boxes.
- **Fluid Responsiveness**: Adapts smoothly from desktop widescreen workstations to tablet clinical carts.
