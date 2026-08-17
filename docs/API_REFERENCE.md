# CareFlow Intelligence API Reference

This document provides a comprehensive specification of all REST endpoints exposed by the CareFlow Intelligence FastAPI backend (`http://localhost:8000`).

---

## 1. Global Specifications

- **Base URL**: `http://localhost:8000`
- **Interactive Swagger UI**: `http://localhost:8000/docs`
- **ReDoc Specification**: `http://localhost:8000/redoc`
- **Standard Content-Type**: `application/json` (unless handling multipart file uploads)
- **CORS Configuration**: Configured via `API_CORS_ORIGINS` (defaults to `http://localhost:3000,http://localhost:3001`).

---

## 2. Patients & Clinical Timeline APIs

### 2.1. List Patients
Returns a paginated list of synthetic patients with optional full-text substring filtering.

- **Method / Path**: `GET /api/patients`
- **Tags**: `patients`
- **Query Parameters**:

| Parameter | Type | Default | Constraints | Description |
| :--- | :--- | :--- | :--- | :--- |
| `search` | `string` | `""` | Max length: 100 | Case-insensitive filter matching first name, last name, city, state, or UUID. |
| `page` | `integer` | `1` | Minimum: 1 | The page index (1-based). |
| `page_size` | `integer` | `20` | Range: 1 – 100 | Number of patient records to return per page. |

- **Response Status**: `200 OK`
- **Response Schema (`PatientListResponse`)**:
```json
{
  "items": [
    {
      "id": "c3e981da-45c1-4045-8123-238491029384",
      "first_name": "John",
      "middle_name": "A.",
      "last_name": "Doe",
      "birth_date": "1975-04-12",
      "death_date": null,
      "gender": "M",
      "city": "Boston",
      "state": "Massachusetts"
    }
  ],
  "page": 1,
  "page_size": 20,
  "total": 100,
  "pages": 5,
  "search": ""
}
```

---

### 2.2. Get Patient Details
Retrieves full demographic details for a specific patient alongside aggregated record counts for encounters, conditions, observations, and medications.

- **Method / Path**: `GET /api/patients/{patient_id}`
- **Tags**: `patients`
- **Path Parameters**:
  - `patient_id` (`UUID`): The unique identifier of the patient.
- **Response Status**: `200 OK` (or `404 Not Found`)
- **Response Schema (`PatientDetail`)**:
```json
{
  "id": "c3e981da-45c1-4045-8123-238491029384",
  "first_name": "John",
  "middle_name": "A.",
  "last_name": "Doe",
  "birth_date": "1975-04-12",
  "death_date": null,
  "gender": "M",
  "city": "Boston",
  "state": "Massachusetts",
  "race": "white",
  "ethnicity": "non-hispanic",
  "postal_code": "02108",
  "stats": {
    "encounters": 48,
    "conditions": 12,
    "observations": 520,
    "medications": 15
  }
}
```

---

### 2.3. Get Unified Patient Timeline
Retrieves a polymorphically aggregated, reverse-chronologically ordered stream of all clinical events associated with a patient (encounters, diagnosed conditions, clinical lab observations, and medication orders).

- **Method / Path**: `GET /api/patients/{patient_id}/timeline`
- **Tags**: `patients`
- **Path Parameters**:
  - `patient_id` (`UUID`): Patient identifier.
- **Query Parameters**:
  - `limit` (`integer`, default: `200`, range: `1..500`): Maximum number of timeline events to return.
- **Response Status**: `200 OK` (or `404 Not Found`)
- **Response Schema (`PatientTimelineResponse`)**:
```json
{
  "patient_id": "c3e981da-45c1-4045-8123-238491029384",
  "events": [
    {
      "id": "enc-10293847-abcd",
      "event_type": "encounter",
      "occurred_at": "2024-02-14T09:30:00Z",
      "ended_at": "2024-02-14T10:15:00Z",
      "category": "ambulatory",
      "code": "185349003",
      "title": "Encounter for check up (procedure)",
      "description": null,
      "value": null,
      "units": null,
      "encounter_id": "enc-10293847-abcd"
    },
    {
      "id": "obs-98765432-efgh",
      "event_type": "observation",
      "occurred_at": "2024-02-14T09:45:00Z",
      "ended_at": null,
      "category": "laboratory",
      "code": "4548-4",
      "title": "Hemoglobin A1c/Hemoglobin.total in Blood",
      "description": "numeric",
      "value": "7.4",
      "units": "%",
      "encounter_id": "enc-10293847-abcd"
    },
    {
      "id": "med-55443322-ijkl",
      "event_type": "medication",
      "occurred_at": "2024-02-14T10:00:00Z",
      "ended_at": null,
      "category": "medication",
      "code": "860975",
      "title": "Metformin hydrochloride 500 MG Oral Tablet",
      "description": "Type 2 diabetes mellitus",
      "value": null,
      "units": null,
      "encounter_id": "enc-10293847-abcd"
    }
  ],
  "returned": 3,
  "limit": 200
}
```

---

## 3. Grounded Chat & Agentic RAG APIs

### 3.1. Submit Chat Query (Grounded Document Assistant)
Executes a clinical inquiry against the document knowledge base. When OpenRouter is configured, it executes a multi-step bounded tool loop (discovering documents and running full-text searches). When unconfigured or upon failure, it gracefully falls back to deterministic extractive retrieval.

- **Method / Path**: `POST /api/chat`
- **Tags**: `chat`
- **Request Body (`ChatRequest`)**:
```json
{
  "question": "What is the recommended eGFR threshold for initiating SGLT2 inhibitors in type 2 diabetes?",
  "session_id": "8f7e6d5c-4b3a-2109-8765-43210fedcba9",
  "document_ids": [
    "12345678-abcd-ef01-2345-6789abcdef01"
  ]
}
```
*Note: `session_id` and `document_ids` are optional. Leaving `document_ids` empty searches across all ready documents.*

- **Response Status**: `200 OK`
- **Response Schema (`ChatResponse`)**:
```json
{
  "session_id": "8f7e6d5c-4b3a-2109-8765-43210fedcba9",
  "answer": "According to the ADA Standards of Care and KDIGO 2023 Guidelines, SGLT2 inhibitors (such as empagliflozin or dapagliflozin) are recommended for patients with type 2 diabetes and chronic kidney disease with an eGFR down to 20 mL/min/1.73 m² [chunk: 104].",
  "citations": [
    {
      "number": 1,
      "document_id": "12345678-abcd-ef01-2345-6789abcdef01",
      "filename": "ADA_Standards_of_Care_2024.md",
      "chunk_id": 104,
      "page_number": 1,
      "excerpt": "SGLT2 inhibitors are recommended in patients with T2D and CKD with eGFR >= 20 mL/min/1.73 m2 to reduce CKD progression and cardiovascular events.",
      "rank": 0.942
    }
  ],
  "grounded": true,
  "response_mode": "agentic_rag_v1",
  "model": "nvidia/nemotron-3-ultra-550b-a55b:free",
  "agent_trace": [
    {
      "step": 1,
      "type": "tool",
      "tool_name": "search_documents",
      "summary": "Ran full-text search with query: 'SGLT2 inhibitor eGFR threshold type 2 diabetes'.",
      "tool_input": {
        "query": "SGLT2 inhibitor eGFR threshold type 2 diabetes"
      },
      "result_count": 4,
      "error_type": null
    },
    {
      "step": 2,
      "type": "answer",
      "tool_name": null,
      "summary": "Generated a grounded answer with 1 citations.",
      "tool_input": {},
      "result_count": 1,
      "error_type": null
    }
  ]
}
```

---

### 3.2. Get Chat Session History
Retrieves all historical user and assistant messages for a specific chat session, including complete citations and agent execution traces.

- **Method / Path**: `GET /api/chat/sessions/{session_id}`
- **Tags**: `chat`
- **Path Parameters**:
  - `session_id` (`UUID`): Session identifier.
- **Response Status**: `200 OK` (or `404 Not Found`)
- **Response Schema (`ChatSessionResponse`)**:
```json
{
  "id": "8f7e6d5c-4b3a-2109-8765-43210fedcba9",
  "title": "What is the recommended eGFR threshold for initiating SGLT2 inhibitors...",
  "messages": [
    {
      "id": "msg-11112222-3333",
      "role": "user",
      "content": "What is the recommended eGFR threshold for initiating SGLT2 inhibitors in type 2 diabetes?",
      "citations": [],
      "response_mode": null,
      "model": null,
      "agent_trace": [],
      "created_at": "2024-08-17T12:00:00Z"
    },
    {
      "id": "msg-44445555-6666",
      "role": "assistant",
      "content": "According to the ADA Standards of Care...",
      "citations": [...],
      "response_mode": "agentic_rag_v1",
      "model": "nvidia/nemotron-3-ultra-550b-a55b:free",
      "agent_trace": [...],
      "created_at": "2024-08-17T12:00:05Z"
    }
  ]
}
```

---

## 4. Document Management & Ingestion APIs

### 4.1. List Indexed Documents
Lists all uploaded or ingested medical reference documents.

- **Method / Path**: `GET /api/documents`
- **Tags**: `documents`
- **Response Status**: `200 OK`
- **Response Schema (`DocumentListResponse`)**:
```json
{
  "documents": [
    {
      "id": "doc-99887766-5544",
      "filename": "FDA_Metformin_Package_Insert.md",
      "content_type": "text/markdown",
      "classification": "public",
      "byte_size": 18450,
      "sha256": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
      "status": "ready",
      "page_count": 1,
      "chunk_count": 14,
      "error_message": null,
      "created_at": "2024-08-17T10:15:30Z"
    }
  ]
}
```

---

### 4.2. Upload Medical Document
Uploads a document (PDF, TXT, Markdown, CSV) to the platform. Computes SHA-256 hash for deduplication, extracts text, performs sliding-window chunking, and persists full-text search vectors.

- **Method / Path**: `POST /api/documents`
- **Tags**: `documents`
- **Content-Type**: `multipart/form-data`
- **Form Fields**:
  - `file` (`UploadFile`): Binary document file (maximum size: 10 MB).
  - `classification` (`string`): Must be `"synthetic"` or `"public"`.
  - `confirm_no_real_patient_data` (`boolean`): Must be `true` (enforces privacy guardrail).
- **Response Status**: `201 Created`
- **Error Codes**:
  - `400 Bad Request`: Invalid classification or missing privacy confirmation.
  - `415 Unsupported Media Type`: File format not in `.pdf, .txt, .md, .csv`.
  - `422 Unprocessable Entity`: File exceeds 10 MB or no extractable text found.

---

## 5. Data Intake Agent APIs

### 5.1. List Available Data Sources
Lists the official pre-approved synthetic data source catalog.

- **Method / Path**: `GET /api/data-agent/sources`
- **Tags**: `data-agent`
- **Response Status**: `200 OK`
- **Response Example**:
```json
{
  "sources": [
    {
      "id": "synthea-sample-latest",
      "name": "Synthea Sample Dataset (Official CSV)",
      "description": "Official MITRE Synthea sample cohort with demographic profiles, encounters, conditions, and medications.",
      "url": "https://synthetichealth.github.io/synthea-sample-data/downloads/latest/synthea_sample_data_csv_latest.zip",
      "format": "zip_csv",
      "sample_size": "100+ synthetic patients"
    }
  ]
}
```

---

### 5.2. Create Intake Job
Triggers background downloading, ZIP extraction, and structural validation of a synthetic dataset.

- **Method / Path**: `POST /api/data-agent/jobs`
- **Tags**: `data-agent`
- **Status Code**: `202 Accepted`
- **Request Body**:
```json
{
  "source_id": "synthea-sample-latest"
}
```
- **Response Schema (`DataAgentJob`)**:
```json
{
  "id": "job-1234-5678-90ab",
  "source_id": "synthea-sample-latest",
  "status": "downloading",
  "archive_sha256": null,
  "manifest": [],
  "validation_errors": [],
  "approved": false,
  "imported": false,
  "import_counts": {},
  "created_at": "2024-08-17T11:00:00Z",
  "completed_at": null
}
```

---

### 5.3. Get Intake Job Status
Polls the live progress, validation checks, and extracted file manifest for an intake job.

- **Method / Path**: `GET /api/data-agent/jobs/{job_id}`
- **Tags**: `data-agent`
- **Status Code**: `200 OK` (or `404 Not Found`)

---

### 5.4. Approve Intake Job (Human-in-the-Loop)
Approves a validated dataset job for database ingestion.

- **Method / Path**: `POST /api/data-agent/jobs/{job_id}/approve`
- **Tags**: `data-agent`
- **Status Code**: `200 OK`
- **Error Codes**:
  - `409 Conflict`: Job is not in the `awaiting_approval` state or has validation errors.

---

### 5.5. Execute Database Import
Starts the transactional database import of approved CSV records into PostgreSQL clinical tables.

- **Method / Path**: `POST /api/data-agent/jobs/{job_id}/import`
- **Tags**: `data-agent`
- **Status Code**: `202 Accepted`

---

## 6. System & Observability APIs

### 6.1. Health Check
Verifies API availability and operational state.

- **Method / Path**: `GET /api/health`
- **Tags**: `health`
- **Response Status**: `200 OK`
```json
{
  "status": "ok",
  "app_name": "CareFlow Intelligence API",
  "app_version": "0.5.0",
  "data_mode": "synthetic",
  "openrouter_enabled": true
}
```

---

### 6.2. Database Status
Queries live record counts across all core clinical tables in PostgreSQL.

- **Method / Path**: `GET /api/database/status`
- **Tags**: `database`
- **Response Status**: `200 OK`
```json
{
  "status": "ok",
  "patients": 10,
  "encounters": 479,
  "conditions": 300,
  "observations": 5368,
  "medications": 296
}
```
