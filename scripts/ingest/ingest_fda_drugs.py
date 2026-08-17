import asyncio
import sys
from pathlib import Path
from typing import Any

import httpx

# Add apps/api and root to python path
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "apps" / "api"))

from app.database import async_session_factory
from scripts.ingest.store_helper import store_medical_document

OPENFDA_ENDPOINT = "https://api.fda.gov/drug/label.json"

DEFAULT_DRUGS = [
    "metformin",
    "lisinopril",
    "atorvastatin",
    "empagliflozin",
    "semaglutide",
    "amoxicillin",
    "levothyroxine",
    "amlodipine",
    "losartan",
    "warfarin",
    "metoprolol",
    "omeprazole",
    "apixaban",
    "gabapentin",
    "hydrochlorothiazide",
]


def format_fda_monograph(drug_name: str, label_data: dict[str, Any]) -> str:
    """Formats FDA label JSON fields into a structured clinical monograph."""
    openfda = label_data.get("openfda", {})
    brand_names = ", ".join(openfda.get("brand_name", [drug_name.capitalize()]))
    generic_name = ", ".join(openfda.get("generic_name", [drug_name.capitalize()]))
    substance = ", ".join(openfda.get("substance_name", []))
    pharm_class = ", ".join(openfda.get("pharm_class_epc", []))

    sections = [
        f"# FDA Clinical Drug Monograph: {generic_name.title()} ({brand_names})",
        f"**Pharmacologic Class**: {pharm_class or 'N/A'}",
        f"**Substance Name**: {substance or generic_name}",
        f"**Source**: US FDA DailyMed Structured Product Labeling (SPL)",
        "\n---",
    ]

    field_mappings = [
        ("Boxed Warnings", "boxed_warning"),
        ("Indications & Usage", "indications_and_usage"),
        ("Dosage & Administration", "dosage_and_administration"),
        ("Dosage Forms & Strengths", "dosage_forms_and_strengths"),
        ("Contraindications", "contraindications"),
        ("Warnings & Precautions", "warnings_and_precautions"),
        ("Adverse Reactions", "adverse_reactions"),
        ("Drug Interactions", "drug_interactions"),
        ("Use in Specific Populations (Pregnancy/Renal/Hepatic)", "use_in_specific_populations"),
        ("Clinical Pharmacology & Mechanism of Action", "clinical_pharmacology"),
    ]

    for title, field_key in field_mappings:
        val = label_data.get(field_key)
        if val and isinstance(val, list):
            text_content = "\n\n".join(str(item).strip() for item in val if str(item).strip())
            if text_content:
                sections.append(f"\n## {title}\n{text_content}")

    return "\n\n".join(sections)


async def fetch_and_store_drug(client: httpx.AsyncClient, drug_name: str) -> bool:
    print(f"[OpenFDA] Fetching monograph for: {drug_name}...")
    params = {
        "search": f'openfda.generic_name:"{drug_name}" OR openfda.brand_name:"{drug_name}"',
        "limit": 1,
    }

    try:
        response = await client.get(OPENFDA_ENDPOINT, params=params, timeout=25.0)
        if response.status_code != 200:
            print(f"[OpenFDA] Failed to fetch {drug_name} (Status: {response.status_code})")
            return False

        data = response.json()
        results = data.get("results", [])
        if not results:
            print(f"[OpenFDA] No FDA label records found for: {drug_name}")
            return False

        label = results[0]
        markdown_content = format_fda_monograph(drug_name, label)
        filename = f"FDA_Monograph_{drug_name.lower().replace(' ', '_')}.md"

        async with async_session_factory() as session:
            result = await store_medical_document(
                session=session,
                filename=filename,
                content=markdown_content,
                classification="public",
                content_type="text/markdown",
            )
            if result.is_duplicate:
                print(f"[OpenFDA] Already indexed: {filename} ({result.chunk_count} chunks)")
            else:
                print(f"[OpenFDA] Successfully stored & indexed: {filename} -> {result.chunk_count} chunks")
            return True

    except Exception as exc:
        print(f"[OpenFDA] Error processing {drug_name}: {exc}")
        return False


async def main(drugs: list[str]):
    async with httpx.AsyncClient() as client:
        tasks = [fetch_and_store_drug(client, drug.strip()) for drug in drugs if drug.strip()]
        results = await asyncio.gather(*tasks)
        success_count = sum(1 for r in results if r)
        print(f"\n[OpenFDA] Completed: {success_count}/{len(drugs)} drug monographs stored in Supabase.")


if __name__ == "__main__":
    drug_list = DEFAULT_DRUGS
    if len(sys.argv) > 1:
        drug_list = sys.argv[1].split(",")
    asyncio.run(main(drug_list))
