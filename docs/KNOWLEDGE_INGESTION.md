# Medical Knowledge Ingestion Suite

To ground AI clinical reasoning in primary biomedical literature, pharmacology, and standard-of-care guidelines, CareFlow Intelligence incorporates a multi-source **Knowledge Ingestion Suite** located in `scripts/ingest/`.

---

## 1. Knowledge Ingestion Architecture

```mermaid
flowchart TD
    subgraph Primary Evidence Sources
        FDA[OpenFDA DailyMed API<br/>FDA Package Inserts]
        PUBMED[NCBI PubMed / PMC E-Utilities<br/>Peer-Reviewed Research]
        GUIDES[Clinical Practice Guidelines<br/>ADA, AHA/ACC, KDIGO, Custom PDFs]
        MEDIA[Clinical Media & Grand Rounds<br/>Lectures & Expert Transcripts]
    end

    subgraph Ingestion Engines (scripts/ingest/)
        I1[ingest_fda_drugs.py]
        I2[ingest_pubmed.py]
        I3[ingest_guidelines.py]
        I4[ingest_media.py]
    end

    subgraph Storage & Indexing Subsystem
        STORE[store_helper.py]
        CHUNK[Sliding-Window Chunking<br/>~1200 chars / 200 overlap]
        HASH[SHA-256 Checksum Deduplication]
    end

    subgraph Database Target
        SUPA[(PostgreSQL 17 / Supabase)]
        DOCS[documents table<br/>Metadata & Status]
        CHUNKS[document_chunks table<br/>persisted to_tsvector + GIN Index]
    end

    FDA --> I1
    PUBMED --> I2
    GUIDES --> I3
    MEDIA --> I4

    I1 & I2 & I3 & I4 --> STORE
    STORE --> HASH --> CHUNK --> DOCS & CHUNKS
    CHUNKS --> SUPA
```

---

## 2. Ingestion Tiers & Components

### Tier 1: OpenFDA Drug Monographs (`ingest_fda_drugs.py`)
Pulls authoritative, structured package inserts from the **OpenFDA DailyMed API** for high-priority medications across diabetes, cardiology, nephrology, anticoagulation, and infectious disease:
- **Drugs Ingested**: Metformin, Semaglutide, Empagliflozin, Dapagliflozin, Tirzepatide, Lisinopril, Losartan, Amlodipine, Atorvastatin, Warfarin, Apixaban, Finerenone, Ceftriaxone, Piperacillin/Tazobactam, Vancomycin.
- **Extracted Clinical Sections**:
  - Boxed Warnings (black-box safety alerts)
  - Indications and Usage
  - Dosage and Administration (including renal dose adjustments)
  - Contraindications
  - Warnings and Precautions
  - Drug Interactions and Pharmacokinetics

```powershell
# Ingest specific drugs from OpenFDA
.\.venv\Scripts\python.exe .\scripts\ingest\ingest_fda_drugs.py "empagliflozin,dapagliflozin,tirzepatide,finerenone"
```

---

### Tier 2: PubMed Research Literature (`ingest_pubmed.py`)
Queries the **NCBI E-Utilities API** (`esearch` + `efetch`) to search and download abstracts and metadata for peer-reviewed clinical trials and review articles:
- **Search Domains**: SGLT2 inhibitors and CKD progression, GLP-1 receptor agonists in cardiovascular outcome trials (CVOTs), Surviving Sepsis Campaign bundles, Anticoagulation in Atrial Fibrillation.
- **Extracted Fields**: PubMed ID (PMID), Title, Authors, Journal, Publication Year, Abstract text, and MeSH terms.

```powershell
# Search and ingest PubMed clinical papers
.\.venv\Scripts\python.exe .\scripts\ingest\ingest_pubmed.py "type 2 diabetes SGLT2 cardiovascular;sepsis resuscitation bundle"
```

---

### Tier 3: Clinical Practice Guidelines (`ingest_guidelines.py`)
Parses and indexes comprehensive clinical guidelines from major professional medical societies:
- **ADA Standards of Care in Diabetes (2024)**: Glycemic targets, first-line pharmacotherapy, renal screening.
- **AHA/ACC Multi-Society Guideline for Hypertension**: Blood pressure thresholds, combination therapy, monitoring.
- **KDIGO Clinical Practice Guideline for Diabetes Management in CKD**: SGLT2i and non-steroidal MRA initiation criteria.
- **Custom PDF Ingestion**: Built-in `pypdf` integration allowing administrators to ingest institutional PDF protocols.

```powershell
# Ingest core clinical guidelines
.\.venv\Scripts\python.exe .\scripts\ingest\ingest_guidelines.py

# Ingest custom guideline PDF
.\.venv\Scripts\python.exe .\scripts\ingest\ingest_guidelines.py "C:\path\to\clinical_guideline.pdf"
```

---

### Tier 4: Grand Rounds & Clinical Media (`ingest_media.py`)
Ingests structured, timestamped transcripts of hospital Grand Rounds lectures, clinical case conferences, and pharmacology review podcasts:
- **Structure**: Title, Presenter/Host, Clinical Topic, Timestamped Sections (e.g. `[05:20] Renal Risk Assessment`), Key Takeaways.
- **Use Case**: Enables the Document Assistant to retrieve real-world clinical nuance and case-based differential discussions.

```powershell
# Ingest Grand Rounds media transcripts
.\.venv\Scripts\python.exe .\scripts\ingest\ingest_media.py
```

---

## 3. Master Ingestion Orchestrator (`scripts/ingest_all.py`)

To run the complete 4-tier ingestion suite in sequence, execute:

```powershell
.\.venv\Scripts\python.exe .\scripts\ingest_all.py
```

This master orchestrator runs all 4 ingestion modules asynchronously, prevents duplicate processing via SHA-256 checking, and reports cumulative document and chunk counts.

---

## 4. Chunking, Deduplication & Database Indexing

### Deduplication Logic (`store_helper.py`)
Before inserting any document:
1. The raw text is encoded to UTF-8 and hashed via **SHA-256**.
2. A lookup queries `documents.sha256`. If a match is found, chunk re-indexing is skipped and the existing document ID is returned.
3. Raw source files are mirrored to `data/documents/<document_id>/source.md`.

### Sliding-Window Text Chunking
- Documents are split into semantic chunks of **1,000 to 1,400 characters** with an overlap of **150 to 200 characters** to ensure clinical context is preserved across chunk boundaries.

### PostgreSQL Full-Text Search Engine
In Supabase/PostgreSQL, `document_chunks` utilizes a persisted computed column:
```sql
search_vector tsvector GENERATED ALWAYS AS (to_tsvector('english', coalesce(content, ''))) STORED;
CREATE INDEX ix_document_chunks_search_vector ON document_chunks USING gin (search_vector);
```
Searches execute high-speed full-text queries:
```sql
SELECT id, content, ts_rank(search_vector, plainto_tsquery('english', :query)) AS rank
FROM document_chunks
WHERE search_vector @@ plainto_tsquery('english', :query)
ORDER BY rank DESC
LIMIT 5;
```
