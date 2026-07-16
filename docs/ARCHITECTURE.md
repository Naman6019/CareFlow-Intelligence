# Architecture

```text
Browser
  |
  v
Next.js web app :3000
  |
  v
FastAPI service :8000
  |
  v
PostgreSQL :5432
```

The initial system only proves the application boundary. Patient ingestion,
document storage, retrieval, and agent tools will be added as separate,
testable steps.

## Safety boundary

- Synthetic data only
- No diagnosis or treatment recommendations
- No autonomous clinical actions
- Human review before any future workflow action

