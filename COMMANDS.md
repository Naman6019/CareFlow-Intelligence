# CareFlow Intelligence: Useful Commands Reference

This document provides a categorized, copy-pasteable reference for running every workflow in CareFlow Intelligence (Docker, Synthea Data Generation, Supabase DB, Knowledge Ingestion Suite, and RAFT Fine-Tuning).

---

## 1. Environment & Dependency Setup

```powershell
# Install core API & ingestion dependencies
pip install -r requirements.txt

# (Optional) Install local ML & LoRA fine-tuning dependencies
pip install -r requirements-ml.txt
```

---

## 2. Application & Docker Operations & Live Logs

```powershell
# Start all containers in the background (API on :8000, Web UI on :3001)
docker compose up -d

# View real-time streaming logs of the FastAPI backend (-f for follow)
docker logs -f careflowintelligence-api-1

# View real-time streaming logs of the Next.js frontend
docker logs -f careflowintelligence-web-1

# View the last 100 log lines with timestamps
docker logs --tail 100 -t careflowintelligence-api-1

# View logs generated in the last 15 minutes
docker logs --since 15m careflowintelligence-api-1

# Stop and remove containers
docker compose down

# Rebuild containers after modifying backend or frontend code
docker compose up -d --build
```

---

## 3. Viewing Logs of Local Background Processes & Studio

```powershell
# Tail / Stream any live log file in real-time (equivalent to 'tail -f' on Linux)
Get-Content -Path "$env:USERPROFILE\.unsloth\studio\tauri.log" -Wait -Tail 50

# View latest Unsloth Studio install/session logs
Get-Content -Path "$env:USERPROFILE\.unsloth\studio\logs\*.log" -Tail 50

# If a Python script was run in the background with output redirection:
# (e.g. Start-Process python -ArgumentList "script.py" -RedirectStandardOutput "output.log")
Get-Content -Path .\output.log -Wait -Tail 50

# Check running PowerShell background jobs
Get-Job
# View the output of a running background job without stopping it:
Receive-Job -Id <JobId> -Keep

# Check active running processes and PIDs (e.g., python, node, uvicorn, ollama)
Get-Process -Name python, node, uvicorn, ollama -ErrorAction SilentlyContinue | Select-Object Id, ProcessName, CPU, WorkingSet64
```

---

## 4. Synthea Synthetic Patient Generation

```powershell
# Generate 100 synthetic patients in Massachusetts (saves CSV + FHIR to data/raw/synthea_output/)
.\scripts\generate_synthea.ps1 -Population 100 -State "Massachusetts"

# Generate 500 patients in Boston
.\scripts\generate_synthea.ps1 -Population 500 -State "Massachusetts" -City "Boston"

# Import generated Synthea CSV cohort into Supabase PostgreSQL
.\.venv\Scripts\python.exe .\scripts\import_synthea_cohort.py
```

---

## 5. Medical Knowledge Ingestion Suite (`scripts/ingest/`)

```powershell
# 1. Run Master Ingestion (Ingests Guidelines, FDA Drug Monographs, PubMed Literature & Media)
.\.venv\Scripts\python.exe .\scripts\ingest_all.py

# 2. Ingest specific drug package inserts / monographs from OpenFDA
.\.venv\Scripts\python.exe .\scripts\ingest\ingest_fda_drugs.py "empagliflozin,dapagliflozin,tirzepatide,finerenone"

# 3. Search and ingest PubMed clinical research papers by topic
.\.venv\Scripts\python.exe .\scripts\ingest\ingest_pubmed.py "type 2 diabetes SGLT2 cardiovascular;sepsis resuscitation bundle"

# 4. Ingest Core Guidelines or custom PDF documents
.\.venv\Scripts\python.exe .\scripts\ingest\ingest_guidelines.py
# (Or pass a custom PDF file / directory):
.\.venv\Scripts\python.exe .\scripts\ingest\ingest_guidelines.py "C:\path\to\clinical_guideline.pdf"

# 5. Ingest Grand Rounds and Clinical Media Transcripts
.\.venv\Scripts\python.exe .\scripts\ingest\ingest_media.py
```

---

## 6. RAFT (Retrieval-Augmented Fine-Tuning) Pipeline (`scripts/raft/`)

```powershell
# 1. Synthesize RAFT clinical dataset with Oracle + Distractor + Abstention sets (e.g. 50 samples)
.\.venv\Scripts\python.exe .\scripts\raft\generate_dataset.py 50

# 2. Format and split raw dataset into 80/20 train/val splits (ChatML & Alpaca formats)
.\.venv\Scripts\python.exe .\scripts\raft\format_dataset.py

# 3. Run Automated Evaluation & Benchmarking Suite (Precision, Recall, Distractor Rejection, Abstention)
.\.venv\Scripts\python.exe .\scripts\raft\evaluate_raft.py

# 4. Fast Local QLoRA Fine-Tuning with Unsloth (Qwen 2.5 7B / 3B + Auto GGUF export)
python .\scripts\raft\train_unsloth_qwen.py --model "unsloth/Qwen2.5-7B-Instruct-bnb-4bit" --epochs 3 --batch-size 2

# 5. Standard HuggingFace PEFT LoRA Fine-Tuning
.\.venv\Scripts\python.exe .\scripts\raft\train_lora.py --model "meta-llama/Meta-Llama-3.1-8B-Instruct" --epochs 3 --batch-size 2

# 6. Deploy Fine-Tuned GGUF to Local Ollama & Connect to CareFlow
# Create Ollama model:
ollama create careflow-qwen -f .\models\careflow_qwen_gguf\Modelfile
# Run local model:
ollama run careflow-qwen
# In .env set:
# OPENROUTER_BASE_URL=http://localhost:11434/v1
# OPENROUTER_MODEL=careflow-qwen
# OPENROUTER_API_KEY=ollama
```

---

## 7. Database Status & API Health Checks

```powershell
# Check database counts and status from API
Invoke-RestMethod -Uri "http://localhost:8000/api/database/status"

# List indexed documents via API
Invoke-RestMethod -Uri "http://localhost:8000/api/documents"

# Fetch first page of patients
(Invoke-RestMethod -Uri "http://localhost:8000/api/patients?page=1").items

# Run Alembic database migrations manually (if schema is updated)
.\.venv\Scripts\python.exe -m alembic upgrade head
```

---

## 8. Access Endpoints

- **Web Interface (Patient Explorer & Grounded Assistant)**: [http://localhost:3001](http://localhost:3001)
- **FastAPI Documentation (Swagger UI)**: [http://localhost:8000/docs](http://localhost:8000/docs)
- **Supabase Cloud Dashboard**: [https://supabase.com/dashboard/project/tvfzgkaujarnseuzpwax](https://supabase.com/dashboard/project/tvfzgkaujarnseuzpwax)
