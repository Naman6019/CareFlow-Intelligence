# Architecture

```text
Browser
  |
  v
Next.js web app :3000
  |
  v
FastAPI service :8000
  |                 |
  v                 v
PostgreSQL :5432  OpenRouter Nemotron
```

The data intake agent uses a bounded workflow:

```text
Approved source
  -> size-limited download
  -> safe ZIP extraction
  -> CSV/schema/reference validation
  -> human approval
  -> idempotent PostgreSQL import
```

Agent jobs and extracted files are stored under `data/intake/<job-id>/`.
Alembic manages the patient, encounter, condition, observation, medication, and
import-run tables.

The patient explorer reads through paginated patient APIs and a unified,
timestamp-ordered timeline query. The browser never queries PostgreSQL directly.

The document assistant stores extracted chunks in PostgreSQL with a generated
full-text search vector. The Document RAG Agent runs a bounded tool loop:

```text
question
  -> Nemotron chooses list_documents or search_documents
  -> FastAPI validates and executes the read-only tool
  -> tool observation returns to Nemotron
  -> Nemotron may reformulate and search again
  -> final answer and chunk IDs are validated
  -> answer or abstention
```

Agent traces are stored with assistant message metadata and returned to the UI.
If OpenRouter is unavailable, unconfigured, exceeds the loop limits, or returns
invalid tool calls/citations, chat falls back to deterministic document
retrieval and the extractive grounded response.

## Safety boundary

- Synthetic data only
- Only selected synthetic/public excerpts may be sent to OpenRouter
- No diagnosis or treatment recommendations
- No autonomous clinical actions
- Human review before any future workflow action
