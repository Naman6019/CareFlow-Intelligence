import asyncio
import sys
import time
from pathlib import Path

# Add apps/api to python path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "apps" / "api"))

import httpx

from scripts.ingest.ingest_fda_drugs import DEFAULT_DRUGS, fetch_and_store_drug
from scripts.ingest.ingest_guidelines import ingest_curated_guidelines
from scripts.ingest.ingest_media import ingest_curated_media
from scripts.ingest.ingest_pubmed import DEFAULT_TOPICS, ingest_topic


async def run_master_ingestion():
    start_time = time.time()
    print("=" * 70)
    print("CAREFLOW INTELLIGENCE: COMPREHENSIVE MEDICAL KNOWLEDGE INGESTION")
    print("=" * 70)

    # 1. Clinical Practice Guidelines
    print("\n>>> STEP 1: Ingesting Gold-Standard Clinical Guidelines (ADA, AHA, KDIGO)")
    await ingest_curated_guidelines()

    # 2. OpenFDA Drug Monograph Ingestion
    print("\n>>> STEP 2: Ingesting OpenFDA Drug Monographs & Safety Warnings")
    async with httpx.AsyncClient() as client:
        fda_tasks = [fetch_and_store_drug(client, drug) for drug in DEFAULT_DRUGS]
        fda_results = await asyncio.gather(*fda_tasks)
        print(f"  [FDA Summary] {sum(1 for r in fda_results if r)}/{len(DEFAULT_DRUGS)} drug monographs processed.")

    # 3. PubMed / PMC Research Literature Ingestion
    print("\n>>> STEP 3: Ingesting PubMed Clinical Research Literature (NCBI E-Utilities)")
    async with httpx.AsyncClient() as client:
        for topic in DEFAULT_TOPICS:
            await ingest_topic(client, topic, limit=3)

    # 4. Clinical Media & Grand Rounds Transcripts
    print("\n>>> STEP 4: Ingesting Multimodal Clinical Media & Grand Rounds Transcripts")
    await ingest_curated_media()

    elapsed = round(time.time() - start_time, 2)
    print("\n" + "=" * 70)
    print(f"ALL MEDICAL KNOWLEDGE INGESTION COMPLETE (Elapsed: {elapsed}s)")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(run_master_ingestion())
