import asyncio
import json
import random
import re
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import httpx
from sqlalchemy import func, select

# Add apps/api and root to python path
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "apps" / "api"))

from app.config import settings
from app.database import async_session_factory
from app.db.models import Condition, Document, DocumentChunk, Encounter, Medication, Observation, Patient

DATASET_DIR = PROJECT_ROOT / "data" / "raft"
DATASET_DIR.mkdir(parents=True, exist_ok=True)


@dataclass
class RAFTDataPoint:
    id: str
    category: str
    question: str
    oracle_chunk_ids: list[int]
    distractor_chunk_ids: list[int]
    all_context_chunk_ids: list[int]
    context_text: str
    chain_of_thought: str
    answer: str
    grounded: bool
    citation_chunk_ids: list[int]


GENERATION_PROMPT = """You are an expert clinical instructor and AI researcher creating training data for RAFT (Retrieval-Augmented Fine-Tuning) in clinical medicine.

You are provided with a PRIMARY CLINICAL SOURCE CHUNK (which contains the ground truth medical facts):
<primary_source chunk_id="{chunk_id}" source="{filename}">
{chunk_content}
</primary_source>

Your task:
1. Formulate a challenging, realistic clinical question that a doctor, nurse, or clinical researcher would ask, whose exact answer is contained in the primary source chunk.
2. Provide a step-by-step Chain-of-Thought (CoT) clinical reasoning:
   - Identify the relevant clinical parameters in the source.
   - Quote the exact numbers, thresholds, drug names, or diagnostic criteria.
   - Explain why this evidence answers the question.
3. Formulate a precise, professional clinical answer that strictly references the evidence using the tag `[chunk: {chunk_id}]`.

Output MUST be a single valid JSON object with EXACTLY this structure:
{{
  "category": "pharmacology | guideline_threshold | clinical_trial | patient_management",
  "question": "<the clinical question>",
  "chain_of_thought": "<step-by-step clinical reasoning quoting the chunk>",
  "answer": "<direct clinical answer with [chunk: {chunk_id}] citations>",
  "grounded": true
}}
"""


async def fetch_available_chunks(limit: int = 200) -> list[dict[str, Any]]:
    """Fetch sample document chunks and patient summaries from Supabase."""
    async with async_session_factory() as session:
        # 1. Fetch document chunks
        doc_chunks = (
            await session.execute(
                select(
                    DocumentChunk.id,
                    DocumentChunk.content,
                    Document.filename,
                    Document.classification,
                )
                .join(Document, DocumentChunk.document_id == Document.id)
                .order_by(func.random())
                .limit(limit)
            )
        ).all()

        chunks = [
            {
                "chunk_id": row.id,
                "content": row.content,
                "filename": row.filename,
                "classification": row.classification,
            }
            for row in doc_chunks
            if len(row.content.strip()) > 150
        ]

        # 2. Fetch patient summaries as synthetic timeline chunks
        patients = (
            await session.execute(
                select(Patient).order_by(func.random()).limit(15)
            )
        ).scalars().all()

        for pat in patients:
            encounters = (
                await session.execute(
                    select(Encounter)
                    .where(Encounter.patient_id == pat.id)
                    .order_by(Encounter.started_at.desc())
                    .limit(5)
                )
            ).scalars().all()

            conditions = (
                await session.execute(
                    select(Condition)
                    .where(Condition.patient_id == pat.id)
                    .order_by(Condition.started_at.desc())
                    .limit(6)
                )
            ).scalars().all()

            meds = (
                await session.execute(
                    select(Medication)
                    .where(Medication.patient_id == pat.id)
                    .order_by(Medication.started_at.desc())
                    .limit(6)
                )
            ).scalars().all()

            timeline_lines = [
                f"Synthetic Patient Profile: {pat.first_name} {pat.last_name} (DOB: {pat.birth_date}, Gender: {pat.gender}, Location: {pat.city}, {pat.state})",
                "Diagnosed Conditions: " + (", ".join(f"{c.description} (onset {c.started_at.date()})" for c in conditions) or "None recorded"),
                "Active & Past Medications: " + (", ".join(f"{m.description} (started {m.started_at.date()})" for m in meds) or "None recorded"),
                "Recent Encounters: " + (", ".join(f"{e.encounter_class} ({e.description}) on {e.started_at.date()}" for e in encounters) or "None recorded"),
            ]
            summary_content = "\n".join(timeline_lines)
            chunks.append({
                "chunk_id": hash(pat.id) % 1000000 + 50000,
                "content": summary_content,
                "filename": f"Patient_Timeline_{pat.last_name}.txt",
                "classification": "synthetic",
            })

        return chunks


async def generate_single_sample(
    client: httpx.AsyncClient,
    oracle_chunk: dict[str, Any],
    distractor_pool: list[dict[str, Any]],
    is_abstention: bool = False,
) -> RAFTDataPoint | None:
    """Uses LLM to synthesize a RAFT training sample."""
    prompt = GENERATION_PROMPT.format(
        chunk_id=oracle_chunk["chunk_id"],
        filename=oracle_chunk["filename"],
        chunk_content=oracle_chunk["content"],
    )

    headers = {
        "Authorization": f"Bearer {settings.openrouter_api_key}",
        "HTTP-Referer": settings.openrouter_site_url,
        "X-Title": settings.openrouter_app_title,
    }

    payload = {
        "model": settings.openrouter_model or "nvidia/nemotron-3-ultra-550b-a55b:free",
        "messages": [
            {"role": "system", "content": "You are a clinical NLP data synthesizer. Always output valid JSON only."},
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.3,
        "response_format": {"type": "json_object"},
    }

    try:
        resp = await client.post(
            f"{settings.openrouter_base_url}/chat/completions",
            json=payload,
            headers=headers,
            timeout=45.0,
        )
        if resp.status_code != 200:
            return None

        raw_json = resp.json()["choices"][0]["message"]["content"]
        match = re.search(r"\{.*\}", raw_json, re.DOTALL)
        if match:
            data = json.loads(match.group(0))
        else:
            data = json.loads(raw_json)

        # Select 2-3 distractor chunks
        distractors = random.sample(
            [d for d in distractor_pool if d["chunk_id"] != oracle_chunk["chunk_id"]],
            k=min(3, len(distractor_pool) - 1),
        )

        if is_abstention:
            # 20% Abstention Case: Present distractors only without the oracle chunk
            all_chunks = distractors
            context_blocks = [
                f"<evidence chunk_id=\"{c['chunk_id']}\" source=\"{c['filename']}\">\n{c['content']}\n</evidence>"
                for c in all_chunks
            ]
            random.shuffle(context_blocks)
            context_text = "\n\n".join(context_blocks)

            return RAFTDataPoint(
                id=f"raft_abs_{random.randint(10000, 99999)}",
                category="abstention_unsupported",
                question=data["question"],
                oracle_chunk_ids=[],
                distractor_chunk_ids=[c["chunk_id"] for c in distractors],
                all_context_chunk_ids=[c["chunk_id"] for c in distractors],
                context_text=context_text,
                chain_of_thought=(
                    "Reasoning: Inspecting all provided evidence chunks. None of the supplied chunks contain information "
                    f"regarding the question '{data['question']}'. The context discusses unrelated topics. "
                    "Therefore, the clinical assistant must abstain rather than fabricate facts."
                ),
                answer="I could not find enough supporting evidence in the provided documents to answer this clinical question.",
                grounded=False,
                citation_chunk_ids=[],
            )

        # Normal RAFT Case: Mix oracle chunk + distractors
        all_chunks = [oracle_chunk] + distractors
        random.shuffle(all_chunks)

        context_blocks = [
            f"<evidence chunk_id=\"{c['chunk_id']}\" source=\"{c['filename']}\">\n{c['content']}\n</evidence>"
            for c in all_chunks
        ]
        context_text = "\n\n".join(context_blocks)

        return RAFTDataPoint(
            id=f"raft_sample_{random.randint(10000, 99999)}",
            category=data.get("category", "clinical_knowledge"),
            question=data["question"],
            oracle_chunk_ids=[oracle_chunk["chunk_id"]],
            distractor_chunk_ids=[c["chunk_id"] for c in distractors],
            all_context_chunk_ids=[c["chunk_id"] for c in all_chunks],
            context_text=context_text,
            chain_of_thought=data.get("chain_of_thought", ""),
            answer=data.get("answer", ""),
            grounded=True,
            citation_chunk_ids=[oracle_chunk["chunk_id"]],
        )

    except Exception as exc:
        print(f"[RAFT Gen] Warning: {exc}")
        return None


async def generate_raft_dataset(target_samples: int = 40):
    print("=" * 65)
    print("CAREFLOW RAFT CLINICAL DATASET SYNTHESIS")
    print(f"Target Samples: {target_samples}")
    print("=" * 65)

    chunks = await fetch_available_chunks(limit=150)
    print(f"[RAFT] Available chunk pool from Supabase: {len(chunks)} chunks.")

    if not chunks:
        print("[RAFT] Error: No chunks found in database. Run ingestion first.")
        return

    dataset: list[RAFTDataPoint] = []
    print(f"[RAFT] Synthesizing {target_samples} clinical QA pairs with CoT & citations...")

    async with httpx.AsyncClient() as client:
        for i in range(target_samples):
            oracle = random.choice(chunks)
            is_abs = random.random() < 0.20
            sample = await generate_single_sample(client, oracle, chunks, is_abstention=is_abs)
            if sample:
                dataset.append(sample)
                status_str = "Abstention Case" if is_abs else f"Oracle Chunk #{sample.oracle_chunk_ids}"
                print(f"  [Sample {len(dataset)}/{target_samples}] ({sample.category}) -> {status_str}")

    out_file = DATASET_DIR / "raft_raw_dataset.json"
    with out_file.open("w", encoding="utf-8") as f:
        json.dump([asdict(d) for d in dataset], f, indent=2)

    print(f"\n[RAFT] Generated {len(dataset)} RAFT data points saved to: {out_file}")

    # Auto-format into ChatML & Alpaca splits
    from scripts.raft.format_dataset import format_dataset
    print("\n[RAFT] Formatting into ChatML train/val splits...")
    format_dataset()


if __name__ == "__main__":
    count = int(sys.argv[1]) if len(sys.argv) > 1 else 30
    asyncio.run(generate_raft_dataset(count))
