"""
CareFlow Intelligence: Precision RAG Query Test
Queries the clinical guideline directly through CareFlow DocumentSearchTool and executes grounded GPU inference.
"""

import asyncio
import sys
import time
from pathlib import Path
import httpx

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "apps" / "api"))

from app.database import async_session_factory
from app.document_agent.retrieval import DocumentSearchTool


async def test_precision_rag(search_query: str, clinical_question: str):
    print("=" * 70)
    print("CAREFLOW LIVE GUIDELINE RAG & INFERENCE TEST")
    print(f"Search Query: \"{search_query}\"")
    print(f"Question:     \"{clinical_question}\"")
    print("=" * 70)

    # 1. Search Supabase
    search_tool = DocumentSearchTool()
    async with async_session_factory() as session:
        results = await search_tool.run(session, question=search_query, document_ids=[], limit=3)

    if not results:
        print("[RAG] No chunks found.")
        return

    print(f"\n[1/2] Retrieved {len(results)} Evidence Chunks:")
    evidence_blocks = []
    for r in results:
        cid = f"chunk_{r.chunk_id}"
        print(f"  - [{cid}] (Rank: {r.rank:.3f}) from {r.filename}")
        evidence_blocks.append(
            f'<evidence chunk_id="{cid}" source="{r.filename}">\n{r.content}\n</evidence>'
        )

    evidence_context = "\n\n".join(evidence_blocks)
    full_prompt = (
        f"{evidence_context}\n\n"
        f"Question: {clinical_question}\n\n"
        "Provide an evidence-based clinical recommendation. Reason step-by-step and cite supporting chunks."
    )

    # 2. Local GPU Inference
    print("\n[2/2] Generating Grounded Decision on RTX 4070 (careflow-qwen)...")
    t0 = time.time()
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            "http://localhost:11434/api/generate",
            json={
                "model": "careflow-qwen",
                "prompt": full_prompt,
                "stream": False,
            },
            timeout=40.0,
        )
    dt = time.time() - t0

    if resp.status_code == 200:
        data = resp.json()
        print(f"\n--- GROUNDED RESPONSE ({dt:.2f}s | {data.get('eval_count',0)/max(dt,0.001):.1f} tok/s) ---")
        print(data.get("response", "").strip())
        print("----------------------------------------------------------------------\n")


if __name__ == "__main__":
    search = "cystitis nitrofurantoin trimethoprim fosfomycin uncomplicated"
    question = "What are the first-line antibiotic regimens for acute uncomplicated cystitis according to IDSA guidelines, and what are the critical contraindications?"
    asyncio.run(test_precision_rag(search, question))
