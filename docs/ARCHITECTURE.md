# System Architecture & C4 Model

CareFlow Intelligence is an enterprise-grade synthetic healthcare operations and research sandbox. The system combines bounded agentic workflows, deterministic knowledge retrieval, and Retrieval-Augmented Fine-Tuning (RAFT) to provide clinically grounded document intelligence and patient timeline exploration.

---

## 1. High-Level Architecture Overview

CareFlow Intelligence is architected as a decoupled, multi-tier distributed system comprising:

1. **Presentation Layer**: A Next.js 15 App Router web application providing a patient explorer, a unified chronological clinical timeline viewer, and a grounded document assistant with real-time agent trace inspection.
2. **API & Orchestration Layer**: A high-performance asynchronous FastAPI service hosting business logic, bounded agent tool loops, dataset ingestion agents, and citation verification engines.
3. **Storage & Persistence Layer**: PostgreSQL 17 (hosted locally via Docker or in the cloud via Supabase) equipped with `pgvector`, persisted `tsvector` generated columns, and GIN full-text indexing.
4. **AI Inference & LLM Providers**: OpenRouter (defaulting to `nvidia/nemotron-3-ultra-550b-a55b:free`) or locally served quantized models (via Ollama on `http://localhost:11434/v1` running fine-tuned Qwen 2.5 GGUF binaries).
5. **Knowledge Ingestion & ML Pipelines**: Background Python pipelines extracting primary medical evidence from OpenFDA DailyMed, PubMed NCBI E-Utilities, Clinical Practice Guidelines (ADA, AHA, KDIGO), and Grand Rounds media.

---

## 2. C4 Architecture Models

### Level 1: System Context Diagram

The System Context diagram illustrates how CareFlow Intelligence fits into the healthcare researcher and clinician workflow, interacting with external knowledge bases and inference providers.

```mermaid
C4Context
    title System Context Diagram - CareFlow Intelligence

    Person(clinician, "Clinician / Researcher", "Explores synthetic patient cohorts, reviews clinical timelines, and queries medical literature.")

    System(careflow, "CareFlow Intelligence System", "Provides synthetic clinical data management, timeline exploration, and grounded document RAG.")

    System_Ext(openrouter, "OpenRouter / External LLMs", "Cloud AI inference provider running Nemotron 3 Ultra or other instruction models.")
    System_Ext(ollama, "Local Ollama Engine", "On-premise / local OpenAI-compatible inference engine running fine-tuned CareFlow Qwen 2.5 GGUF.")
    System_Ext(openfda, "OpenFDA DailyMed API", "Federal drug database providing structured package inserts, boxed warnings, and dosing.")
    System_Ext(pubmed, "NCBI PubMed E-Utilities", "National Library of Medicine repository for biomedical literature and clinical trials.")
    System_Ext(synthea_repo, "MITRE Synthea Repository", "Official open-source synthetic health record generator.")

    Rel(clinician, careflow, "Interacts via Web UI (Port 3001) / REST APIs (Port 8000)")
    Rel(careflow, openrouter, "Sends bounded tool loop prompts & context (HTTPS)")
    Rel(careflow, ollama, "Sends local inference queries (HTTP)")
    Rel(careflow, openfda, "Ingests drug monographs & pharmacokinetics (HTTPS)")
    Rel(careflow, pubmed, "Ingests peer-reviewed clinical research (HTTPS)")
    Rel(careflow, synthea_repo, "Downloads official sample datasets (HTTPS)")
```

---

### Level 2: Container Diagram

The Container diagram breaks down the CareFlow Intelligence boundary into its constituent runtime containers and data stores.

```mermaid
C4Container
    title Container Diagram - CareFlow Intelligence

    Person(user, "Clinician / User", "Web Browser")

    Container(web_app, "Frontend Web Application", "Next.js 15, React, TypeScript, Vanilla CSS", "Renders Patient Explorer, Clinical Timeline, Grounded Chat Assistant, and Live Agent Trace Inspector.", "Port 3001")
    
    Container(api_service, "Backend API Service", "FastAPI, Python 3.12, SQLAlchemy Async, Pydantic", "Exposes REST endpoints, manages data intake agent, executes bounded agentic tool loops, and validates citations.", "Port 8000")

    ContainerDb(db_postgres, "Database & Search Store", "PostgreSQL 17 + pgvector + GIN Indexing", "Stores synthetic patients, encounters, conditions, observations, medications, documents, and document chunks with tsvector.", "Port 5432 / Supabase")

    Container(ml_pipeline, "RAFT & Ingestion Pipelines", "Python 3.12, Unsloth, PyTorch, HuggingFace", "Generates RAFT datasets with distractors/abstentions, trains 4-bit QLoRA models, and ingests medical guidelines.")

    Container(ollama_local, "Local Inference Engine (Optional)", "Ollama, GGUF Q4_K_M", "Provides zero-cost, privacy-compliant local LLM inference for fine-tuned models.", "Port 11434")

    Rel(user, web_app, "Navigates and queries", "HTTPS / HTTP")
    Rel(web_app, api_service, "Sends API requests & chat queries", "JSON / HTTP")
    Rel(api_service, db_postgres, "Reads/writes patient records & document chunks", "asyncpg / SQL")
    Rel(api_service, ollama_local, "Queries fine-tuned model (if configured)", "HTTP / REST")
    Rel(ml_pipeline, db_postgres, "Pulls literature chunks & stores ingested documents", "SQL / asyncpg")
```

---

### Level 3: Component Diagram (Backend API Service)

The Component diagram details the internal modular structure of the FastAPI backend service (`apps/api/app`).

```mermaid
C4Component
    title Component Diagram - FastAPI Backend Service

    Container_Boundary(api_service, "FastAPI Service (apps/api/app)") {
        Component(router_patients, "Patients Router", "FastAPI APIRouter", "Handles patient listing, search filters, detail aggregation, and unified timeline queries.")
        Component(router_chat, "Chat & RAG Router", "FastAPI APIRouter", "Handles conversational sessions, message history, and routes queries to Agentic or Extractive pipelines.")
        Component(router_docs, "Documents Router", "FastAPI APIRouter", "Handles multipart file uploads, SHA-256 deduplication, text extraction (PDF/TXT/MD), and chunk indexing.")
        Component(router_data_agent, "Data Intake Router", "FastAPI APIRouter", "Orchestrates background download, validation, approval, and import of Synthea datasets.")
        Component(router_status, "Database Status Router", "FastAPI APIRouter", "Reports real-time record counts across all core clinical tables.")

        Component(doc_agent, "Document RAG Agent", "CareFlowDocumentAgent", "Controls the iterative tool loop (list_documents, search_documents), reformulates queries, and verifies citation fidelity.")
        Component(synthesis_engine, "Synthesis & Fallback Engine", "synthesis.py & retrieval.py", "Parses JSON responses, verifies citation chunk IDs, and falls back to deterministic retrieval on failure.")
        Component(data_intake_service, "Data Intake Service", "DataIntakeAgent", "Executes download, ZIP slip validation, header schema checks, and initiates transactional imports.")
        Component(synthea_importer, "Synthea Importer", "SyntheaImporter", "Performs batch upserts into PostgreSQL tables with foreign-key cascade management.")
        Component(chunking_engine, "Chunking & Parser Module", "chunking.py", "Extracts text from PDF/TXT/MD, applies sliding window chunking with configurable overlap.")
    }

    ContainerDb(db, "PostgreSQL Database", "PostgreSQL 17", "Stores clinical tables & search vectors")
    System_Ext(openrouter_api, "OpenRouter API", "Cloud LLM Provider")

    Rel(router_patients, db, "Queries patients & timeline events", "SQL")
    Rel(router_docs, chunking_engine, "Passes uploaded documents for parsing", "Python Call")
    Rel(router_docs, db, "Inserts documents & chunks", "SQL")
    Rel(router_chat, doc_agent, "Delegates question answering", "Python Async Call")
    Rel(doc_agent, openrouter_api, "Calls LLM with tools & messages", "HTTPS JSON")
    Rel(doc_agent, synthesis_engine, "Validates model payload & citations", "Python Call")
    Rel(doc_agent, db, "Executes full-text search via tools", "SQL tsvector")
    Rel(router_data_agent, data_intake_service, "Triggers background jobs", "Python Call")
    Rel(data_intake_service, synthea_importer, "Calls batch importer upon human approval", "Python Call")
    Rel(synthea_importer, db, "Performs bulk upserts", "SQL asyncpg")
```

---

## 3. Core Execution Workflows & Data Flows

### A. Document RAG Agentic Tool Loop

The Document RAG Agent runs a strictly bounded, non-parametric reasoning loop:

```mermaid
sequenceDiagram
    autonumber
    actor User as User / Clinician
    participant UI as Next.js Web UI
    participant API as FastAPI /api/chat
    participant Agent as CareFlowDocumentAgent
    participant LLM as OpenRouter / Nemotron
    participant DB as PostgreSQL (pgvector / tsvector)
    participant Synth as Synthesis & Citation Validator

    User->>UI: Submit clinical query + document scope
    UI->>API: POST /api/chat { question, document_ids }
    API->>Agent: run(session, question, document_ids)
    
    loop Bounded Tool Loop (Max 4 Iterations, Max 3 Tool Calls)
        Agent->>LLM: POST /chat/completions (System prompt + Tools + User Question)
        LLM-->>Agent: Returns Tool Call (e.g. search_documents(query="..."))
        Agent->>DB: Execute PostgreSQL full-text search (to_tsvector @@ plainto_tsquery)
        DB-->>Agent: Return matching chunks (chunk_id, content, score)
        Agent->>LLM: Send tool execution result
    end

    LLM-->>Agent: Returns final JSON payload { answer, citation_chunk_ids, grounded }
    Agent->>Synth: Validate JSON payload & verify citation_chunk_ids match retrieved chunks
    
    alt Validation Succeeded
        Synth-->>API: Validated answer + verified citation objects
    else Validation Failed / Timeout / Tool Error
        API->>DB: Execute deterministic fallback search
        DB-->>API: Fallback chunks
        API->>Synth: Build extractive grounded response
    end

    API->>DB: Save chat message & agent trace
    API-->>UI: Return ChatResponse { answer, citations, agent_trace, response_mode }
    UI-->>User: Display answer with clickable citations and expandable trace inspector
```

---

### B. Synthea Data Intake & Human-in-the-Loop Pipeline

To prevent unauthorized data ingestion, all dataset imports follow a 5-stage bounded pipeline:

```mermaid
flowchart TD
    A[Approved Source Catalog] -->|1. Download| B[Size-Bounded Temp Download<br/>Max 50 MB]
    B -->|2. Safe Extraction| C[ZIP Slip Protection & Size Guard<br/>Max 250 MB]
    C -->|3. Validation Stage| D[Validate CSV Headers, UUIDs, Foreign Keys]
    D -->|4. Awaiting Approval| E{Human-in-the-Loop<br/>Approval Gate}
    E -->|Rejected| F[Purge Temp Workspace]
    E -->|Approved via UI| G[SyntheaImporter Async Pipeline]
    G -->|5. Idempotent Upsert| H[(PostgreSQL Clinical Tables)]
    H --> I[Record DataImportRun with SHA-256 Checksum]
```

---

## 4. Safety Boundaries & Clinical Guardrails

CareFlow Intelligence enforces rigorous clinical and system safety boundaries:

1. **Synthetic Data Sandbox**: The platform is restricted to synthetic datasets (MITRE Synthea) and public biomedical literature. Real Protected Health Information (PHI) is blocked at ingestion.
2. **Untrusted Retrieval Principle**: Retrieved document chunks and tool results are treated as *untrusted evidence*, never as system instructions. This prevents indirect prompt injection via uploaded documents.
3. **Non-Parametric Grounding**: The agent's system prompt strictly prohibits relying on pre-trained parametric weights for clinical facts. All claims must be cited using `[chunk: ID]`.
4. **Mandatory Citation Verification**: The API backend validates that every cited chunk ID was actually retrieved and observed during that specific session. If an invalid citation or hallucinated chunk ID is detected, the system immediately rejects the output and triggers the deterministic extractive fallback.
5. **No Autonomous Clinical Decision Making**: The system explicitly disclaims diagnostic and prescribing capabilities, acting purely as an informational and research companion.
