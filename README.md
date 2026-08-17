# CareFlow Intelligence

Synthetic healthcare operations and research sandbox.

## Run

```powershell
Copy-Item .env.example .env -ErrorAction SilentlyContinue
# Set OPENROUTER_API_KEY in .env without committing it.
docker compose up --build
```

Open http://localhost:3000 and select **Find Synthea data**.

The data intake agent downloads the official MITRE Synthea CSV sample, validates
it, requires approval, and imports the patient timeline subset into PostgreSQL.

Database migrations run automatically when the API container starts.

Database counts are available at http://localhost:8000/api/database/status.

Patient explorer:

- http://localhost:3000/patients
- `GET /api/patients?search=&page=1`
- `GET /api/patients/{patient_id}`
- `GET /api/patients/{patient_id}/timeline`

Grounded document assistant:

- http://localhost:3000/assistant
- `POST /api/documents`
- `GET /api/documents`
- `POST /api/chat`

Only synthetic or public documents are allowed. The first Agentic RAG agent
uses OpenRouter Nemotron 3 Ultra to choose and call two read-only tools:

- `list_documents` discovers ready sources in the selected scope.
- `search_documents` runs bounded PostgreSQL full-text retrieval and may be
  called again with a reformulated query.

Citation chunk IDs are validated by the API before the answer is returned. The
agent is limited to four model iterations and three tool calls. Missing keys,
provider errors, invalid tool calls, and invalid citations fall back to the
extractive grounded response.

The configured model is:

```text
nvidia/nemotron-3-ultra-550b-a55b:free
```

OpenRouter free-model limits are suitable for learning and low-volume demos,
not unrestricted production traffic.