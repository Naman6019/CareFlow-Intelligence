import asyncio
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any

import httpx

# Add apps/api and root to python path
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "apps" / "api"))

from app.database import async_session_factory
from scripts.ingest.store_helper import store_medical_document

NCBI_SEARCH_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
NCBI_FETCH_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"

DEFAULT_TOPICS = [
    "type 2 diabetes management SGLT2 GLP1",
    "hypertension guideline directed medical therapy AHA ACC",
    "heart failure reduced ejection fraction GDMT",
    "chronic kidney disease KDIGO guidelines proteinuria",
    "sepsis surviving sepsis campaign management bundle",
]


async def search_pubmed(client: httpx.AsyncClient, query: str, limit: int = 4) -> list[str]:
    """Search PubMed for article PMIDs."""
    params = {
        "db": "pubmed",
        "term": query,
        "retmax": str(limit),
        "retmode": "json",
        "sort": "pub_date",
    }
    response = await client.get(NCBI_SEARCH_URL, params=params, timeout=20.0)
    if response.status_code != 200:
        print(f"[PubMed] Search error for '{query}': {response.status_code}")
        return []
    data = response.json()
    return data.get("esearchresult", {}).get("idlist", [])


async def fetch_pubmed_articles(client: httpx.AsyncClient, pmids: list[str]) -> list[dict[str, Any]]:
    """Fetch full article metadata & abstracts using efetch XML."""
    if not pmids:
        return []

    params = {
        "db": "pubmed",
        "id": ",".join(pmids),
        "retmode": "xml",
    }
    response = await client.get(NCBI_FETCH_URL, params=params, timeout=30.0)
    if response.status_code != 200:
        print(f"[PubMed] Fetch error for PMIDs {pmids}: {response.status_code}")
        return []

    articles = []
    try:
        root = ET.fromstring(response.text)
        for article_el in root.findall(".//PubmedArticle"):
            pmid_el = article_el.find(".//MedlineCitation/PMID")
            pmid = "".join(pmid_el.itertext()).strip() if pmid_el is not None else "Unknown"

            title_el = article_el.find(".//ArticleTitle")
            title = "".join(title_el.itertext()).strip() if title_el is not None else "Untitled Medical Article"
            if not title:
                title = "Untitled Medical Article"

            journal_el = article_el.find(".//Journal/Title")
            journal = "".join(journal_el.itertext()).strip() if journal_el is not None else "Medical Journal"

            # Publication year
            year_el = article_el.find(".//JournalIssue/PubDate/Year")
            year = "".join(year_el.itertext()).strip() if year_el is not None else "Recent"

            # Authors
            authors = []
            for author_el in article_el.findall(".//AuthorList/Author"):
                last = author_el.find("LastName")
                first = author_el.find("ForeName")
                last_txt = "".join(last.itertext()).strip() if last is not None else ""
                first_txt = "".join(first.itertext()).strip() if first is not None else ""
                if last_txt:
                    authors.append(f"{last_txt} {first_txt}".strip())
            authors_str = ", ".join(authors[:5]) + (" et al." if len(authors) > 5 else "")

            # Abstract sections
            abstract_parts = []
            for abs_text in article_el.findall(".//Abstract/AbstractText"):
                label = abs_text.attrib.get("Label", "")
                text = "".join(abs_text.itertext()).strip()
                if label:
                    abstract_parts.append(f"**{label}**: {text}")
                elif text:
                    abstract_parts.append(text)
            abstract = "\n\n".join(abstract_parts) if abstract_parts else "No abstract provided."

            # MeSH terms
            mesh_terms = []
            for mesh_el in article_el.findall(".//MeshHeadingList/MeshHeading/DescriptorName"):
                txt = "".join(mesh_el.itertext()).strip()
                if txt:
                    mesh_terms.append(txt)

            articles.append({
                "pmid": pmid,
                "title": title,
                "journal": journal,
                "year": year,
                "authors": authors_str or "Authors listed in PubMed",
                "abstract": abstract,
                "mesh_terms": mesh_terms,
            })
    except Exception as exc:
        print(f"[PubMed] XML parsing error: {exc}")

    return articles


def format_pubmed_markdown(article: dict[str, Any]) -> str:
    mesh_formatted = ", ".join(article["mesh_terms"]) if article["mesh_terms"] else "Clinical Studies"
    return f"""# {article['title']}

**Authors**: {article['authors']}  
**Journal**: {article['journal']} ({article['year']})  
**PMID**: [{article['pmid']}](https://pubmed.ncbi.nlm.nih.gov/{article['pmid']}/)  
**MeSH Headings**: {mesh_formatted}  

---

## Abstract & Clinical Findings

{article['abstract']}

## Clinical Relevance & Evidence Summary
This study was indexed from the National Library of Medicine (NCBI PubMed) database for reference in clinical decision support and literature synthesis.
"""


async def ingest_topic(client: httpx.AsyncClient, topic: str, limit: int = 3):
    print(f"\n[PubMed] Querying topic: '{topic}'...")
    pmids = await search_pubmed(client, topic, limit=limit)
    if not pmids:
        print(f"[PubMed] No articles found for '{topic}'")
        return

    articles = await fetch_pubmed_articles(client, pmids)
    print(f"[PubMed] Retrieved {len(articles)} articles. Indexing into Supabase...")

    async with async_session_factory() as session:
        for art in articles:
            content = format_pubmed_markdown(art)
            clean_title = re.sub(r"[^\w\s-]", "", art.get("title") or "Article").strip().replace(" ", "_")[:40]
            filename = f"PubMed_{art['pmid']}_{clean_title}.md"
            res = await store_medical_document(
                session=session,
                filename=filename,
                content=content,
                classification="public",
                content_type="text/markdown",
            )
            if res.is_duplicate:
                print(f"  [Exists] {filename} ({res.chunk_count} chunks)")
            else:
                print(f"  [Indexed] {filename} -> {res.chunk_count} chunks (PMID: {art['pmid']})")


async def main(topics: list[str], limit_per_topic: int = 3):
    async with httpx.AsyncClient() as client:
        for topic in topics:
            await ingest_topic(client, topic.strip(), limit=limit_per_topic)
    print("\n[PubMed] Literature ingestion completed successfully.")


if __name__ == "__main__":
    query_topics = DEFAULT_TOPICS
    if len(sys.argv) > 1:
        query_topics = sys.argv[1].split(";")
    asyncio.run(main(query_topics))
