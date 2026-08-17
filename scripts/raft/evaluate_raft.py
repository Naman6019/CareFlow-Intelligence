import asyncio
import json
import re
import sys
from pathlib import Path
from typing import Any

import httpx

# Add apps/api and root to python path
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "apps" / "api"))

from app.config import settings

DATA_DIR = PROJECT_ROOT / "data" / "raft"


async def evaluate_sample(client: httpx.AsyncClient, sample: dict[str, Any], model_name: str) -> dict[str, Any]:
    prompt = f"### Clinical Context:\n{sample['context_text']}\n\n### Question:\n{sample['question']}"

    headers = {
        "Authorization": f"Bearer {settings.openrouter_api_key}",
        "HTTP-Referer": settings.openrouter_site_url,
        "X-Title": settings.openrouter_app_title,
    }

    payload = {
        "model": model_name,
        "messages": [
            {
                "role": "system",
                "content": (
                    "You are CareFlow Intelligence. Answer strictly based on the provided evidence blocks. "
                    "Cite supporting chunks with `[chunk: <id>]`. If evidence is missing, state so clearly."
                ),
            },
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.1,
    }

    try:
        resp = await client.post(
            f"{settings.openrouter_base_url}/chat/completions",
            json=payload,
            headers=headers,
            timeout=40.0,
        )
        if resp.status_code != 200:
            return {"error": f"API error: {resp.status_code}"}

        output_text = resp.json()["choices"][0]["message"]["content"]

        # Extract cited chunk IDs
        cited_ids = [
            int(cid) for cid in re.findall(r"\[chunk\s*:\s*(\d+)\]", output_text, flags=re.IGNORECASE)
        ]

        oracle_ids = set(sample.get("oracle_chunk_ids", []))
        distractor_ids = set(sample.get("distractor_chunk_ids", []))
        is_abstention_sample = not sample.get("grounded", True) or len(oracle_ids) == 0

        # Metrics computation
        cited_set = set(cited_ids)
        
        # 1. Distractor Rejection (Did the model cite any distractor?)
        cited_distractors = cited_set.intersection(distractor_ids)
        distractor_rejected = len(cited_distractors) == 0

        # 2. Citation Precision & Recall
        if oracle_ids:
            true_positives = len(cited_set.intersection(oracle_ids))
            citation_precision = (true_positives / len(cited_set)) if cited_set else 0.0
            citation_recall = true_positives / len(oracle_ids)
        else:
            citation_precision = 1.0 if len(cited_set) == 0 else 0.0
            citation_recall = 1.0 if len(cited_set) == 0 else 0.0

        # 3. Abstention Accuracy
        abstention_words = ["not find enough", "insufficient", "not enough supporting", "no information", "cannot answer"]
        model_abstained = any(w in output_text.lower() for w in abstention_words)
        abstention_correct = (model_abstained == is_abstention_sample)

        return {
            "id": sample["id"],
            "category": sample["category"],
            "model_output": output_text,
            "cited_ids": cited_ids,
            "oracle_ids": list(oracle_ids),
            "citation_precision": citation_precision,
            "citation_recall": citation_recall,
            "distractor_rejected": distractor_rejected,
            "abstention_correct": abstention_correct,
            "is_abstention_sample": is_abstention_sample,
        }

    except Exception as exc:
        return {"error": str(exc)}


async def run_benchmark(val_file: Path | None = None, model_name: str | None = None):
    target_file = val_file or (DATA_DIR / "raft_raw_dataset.json")
    if not target_file.exists():
        print(f"Error: {target_file} not found. Run generate_dataset.py first.")
        return

    with target_file.open("r", encoding="utf-8") as f:
        samples = json.load(f)

    eval_model = model_name or settings.openrouter_model or "nvidia/nemotron-3-ultra-550b-a55b:free"
    print("=" * 65)
    print(f"CAREFLOW RAFT EVALUATION & BENCHMARK HARNESS")
    print(f"Evaluation Model: {eval_model}")
    print(f"Evaluation Samples: {len(samples)}")
    print("=" * 65)

    results = []
    async with httpx.AsyncClient() as client:
        for idx, sample in enumerate(samples[:15], start=1):
            print(f"  Evaluating [{idx}/{min(15, len(samples))}] ({sample.get('category')})...", end="", flush=True)
            res = await evaluate_sample(client, sample, eval_model)
            if "error" not in res:
                results.append(res)
                print(f" Done (Precision: {res['citation_precision']:.2f}, Recall: {res['citation_recall']:.2f})")
            else:
                print(f" Failed ({res['error']})")

    if not results:
        print("No successful evaluations.")
        return

    avg_prec = sum(r["citation_precision"] for r in results) / len(results)
    avg_rec = sum(r["citation_recall"] for r in results) / len(results)
    distractor_rejection_rate = sum(1 for r in results if r["distractor_rejected"]) / len(results)
    abstention_acc = sum(1 for r in results if r["abstention_correct"]) / len(results)

    print("\n" + "=" * 65)
    print("BENCHMARK RESULTS SUMMARY")
    print("=" * 65)
    print(f"  • Citation Precision:         {avg_prec * 100:.1f}%")
    print(f"  • Citation Recall:            {avg_rec * 100:.1f}%")
    print(f"  • Distractor Rejection Rate:  {distractor_rejection_rate * 100:.1f}%")
    print(f"  • Abstention Accuracy:        {abstention_acc * 100:.1f}%")
    print("=" * 65)


if __name__ == "__main__":
    asyncio.run(run_benchmark())
