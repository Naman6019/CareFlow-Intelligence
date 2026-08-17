"""
CareFlow Intelligence: Live Production RAG Retrieval & Inference Test
Uses CareFlow's actual DocumentSearchTool to query Supabase full-text & vector indices,
then runs local clinical synthesis on RTX 4070.
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


async def test_careflow_production_rag(query: str):
    print("=" * 70)
    print("CAREFLOW PRODUCTION RAG PIPELINE (SUPABASE + LOCAL OLLAMA)")
    print(f"Clinical Query: \"{query}\"")
    print("=" * 70)

    # 1. Real CareFlow Document Search
    print("\n[1/2] Executing DocumentSearchTool over Supabase Clinical Knowledge Base...")
    search_tool = DocumentSearchTool()
    async with async_session_factory() as session:
        results = await search_tool.run(session, question=query, document_ids=[], limit=5)

    if not results:
        print("[RAG Error] No relevant clinical chunks found in Supabase.")
        return

    print(f"[RAG Success] Retrieved {len(results)} highly-ranked clinical chunks:")
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
        f"Question: {query}\n\n"
        "Provide an evidence-based clinical recommendation. Reason step-by-step and cite supporting chunks."
    )

    # 2. Local GPU Inference
    print("\n[2/2] Running Grounded Inference on NVIDIA RTX 4070 (careflow-qwen)...")
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
        print(f"\n--- GROUNDED CLINICAL DECISION ({dt:.2f}s | {data.get('eval_count',0)/max(dt,0.001):.1f} tok/s) ---")
        print(data.get("response", "").strip())
        print("----------------------------------------------------------------------\n")
    else:
        print(f"Error {resp.status_code}: {resp.text}")


if __name__ == "__main__":
    test_query = "What is the recommended first-line antibiotic for uncomplicated cystitis in a patient with a documented penicillin allergy?"
    asyncio.run(test_careflow_production_rag(test_query))
