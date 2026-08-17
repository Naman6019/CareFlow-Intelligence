# Deployment & Operations Runbook

This guide covers deployment strategies, environment configurations, cloud database setups, container orchestration, log streaming, and operational runbooks for CareFlow Intelligence.

---

## 1. Deployment Topologies

CareFlow Intelligence supports two primary deployment topologies:

```mermaid
flowchart TD
    subgraph Topology A: Local Docker Sandbox
        A1[Next.js Web Container :3001]
        A2[FastAPI API Container :8000]
        A3[Local PostgreSQL Container :5432]
        A1 --> A2 --> A3
        A2 --> A4[OpenRouter / Local Ollama]
    end

    subgraph Topology B: Production Hybrid Cloud
        B1[Vercel / Next.js Cluster]
        B2[Cloud API Cluster<br/>FastAPI / AWS ECS / Fly.io]
        B3[(Supabase PostgreSQL 17<br/>pgvector + Supavisor)]
        B1 --> B2 --> B3
        B2 --> B4[OpenRouter / On-Prem vLLM]
    end
```

---

## 2. Environment Variables Specification

Create your `.env` file in the project root based on `.env.example`:

```powershell
Copy-Item .env.example .env
```

### Complete Environment Variable Reference

| Variable Name | Default Value | Description |
| :--- | :--- | :--- |
| `DATABASE_URL` | `postgresql+asyncpg://careflow:careflow@localhost:5432/careflow` | Asynchronous SQLAlchemy connection string. For Supabase, use port `5432` (direct) or `6543` (transaction pooler). |
| `API_CORS_ORIGINS` | `http://localhost:3000,http://localhost:3001` | Comma-separated allowed CORS origins for the FastAPI backend. |
| `DATA_MODE` | `synthetic` | Enforces synthetic data sandbox isolation rules. |
| `OPENROUTER_API_KEY` | `""` | OpenRouter API Key for cloud model inference (leave empty for local fallback). |
| `OPENROUTER_BASE_URL`| `https://openrouter.ai/api/v1` | Base URL for LLM provider (set to `http://localhost:11434/v1` for local Ollama). |
| `OPENROUTER_MODEL` | `nvidia/nemotron-3-ultra-550b-a55b:free` | Model identifier for agent tool loops and synthesis. |
| `OPENROUTER_TIMEOUT_SECONDS` | `75.0` | HTTP request timeout for model completions. |
| `OPENROUTER_SITE_URL`| `http://localhost:3001` | Referer URL sent to OpenRouter API headers. |
| `OPENROUTER_APP_TITLE`| `CareFlow Intelligence` | App title sent in OpenRouter attribution headers. |
| `AGENT_MAX_ITERATIONS` | `4` | Maximum allowable reasoning iterations in the Document RAG agent loop. |
| `AGENT_MAX_TOOL_CALLS` | `3` | Maximum number of tool calls permitted before forcing synthesis or abstention. |
| `AGENT_MAX_DOWNLOAD_BYTES` | `52428800` (50 MB) | Upper limit for remote dataset download archives. |
| `AGENT_MAX_EXTRACTED_BYTES` | `262144000` (250 MB) | Upper limit for uncompressed ZIP extractions. |
| `DOCUMENT_MAX_UPLOAD_BYTES` | `10485760` (10 MB) | Maximum allowable file size for uploaded literature documents. |

---

## 3. Docker Compose Orchestration

### Start the Full Stack
```powershell
# Build and run containers in background
docker compose up -d --build
```

### Container Endpoints:
- **Frontend Web UI**: `http://localhost:3001`
- **Backend API Service**: `http://localhost:8000`
- **PostgreSQL Database**: `localhost:5432`

### Stop the Full Stack
```powershell
docker compose down
```

---

## 4. Supabase Cloud Database Configuration

CareFlow is tested and optimized with **Supabase PostgreSQL 17.6.1** equipped with `pgvector` and `Supavisor` connection pooling.

### Setup Steps:
1. In the Supabase Dashboard, create a project (e.g. `CareFlow-Intelligence`).
2. Obtain the connection string under **Project Settings > Database > Connection Strings > URI**.
3. In `.env`, configure:
   ```env
   DATABASE_URL=postgresql+asyncpg://postgres.<project-ref>:<db-password>@aws-0-ap-south-1.pooler.supabase.com:6543/postgres
   ```
4. Execute Alembic schema migrations:
   ```powershell
   .\.venv\Scripts\python.exe -m alembic upgrade head
   ```

---

## 5. Operational Runbooks & Troubleshooting

### Scenario A: Streaming Real-Time Container Logs
```powershell
# Stream live logs from the backend API (-f for follow)
docker logs -f careflowintelligence-api-1

# Stream live logs from the Next.js frontend
docker logs -f careflowintelligence-web-1

# View last 100 log lines with timestamps
docker logs --tail 100 -t careflowintelligence-api-1
```

---

### Scenario B: Inspecting Background Python Jobs & Unsloth Studio
```powershell
# Stream Unsloth Studio desktop GUI logs
Get-Content -Path "$env:USERPROFILE\.unsloth\studio\tauri.log" -Wait -Tail 50

# Check active Python and Node processes
Get-Process -Name python, node, uvicorn, ollama -ErrorAction SilentlyContinue | Select-Object Id, ProcessName, CPU, WorkingSet64
```

---

### Scenario C: Unsloth Studio Installation GitHub Rate-Limiting (HTTP 429)
**Symptom**: Unsloth Studio installer stalls on step 11/12 (`diffusers pin`).  
**Cause**: GitHub rate-limits unauthenticated zip downloads from `codeload.github.com`.  
**Resolution**:
1. Open PowerShell and navigate to the isolated studio environment:
   ```powershell
   cd $env:USERPROFILE\.unsloth\studio\unsloth_studio
   ```
2. Install `diffusers` directly via Git:
   ```powershell
   .\Scripts\pip.exe install git+https://github.com/huggingface/diffusers.git@f53d552036a0d1bd5570782a39cd40cfabf112bc
   ```

---

### Scenario D: OpenRouter Free Model Rate Limiting
**Symptom**: Document assistant chat returns status `fallback` or `The agent could not complete its bounded tool loop`.  
**Cause**: OpenRouter's free tier (`nvidia/nemotron-3-ultra-550b-a55b:free`) has dynamic per-minute request limits.  
**Resolution**:
1. CareFlow's built-in **extractive grounded fallback** will automatically handle the query deterministically.
2. Alternatively, switch to local Ollama inference by pointing `OPENROUTER_BASE_URL` to `http://localhost:11434/v1`.
