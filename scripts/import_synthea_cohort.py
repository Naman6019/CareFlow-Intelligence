import asyncio
import hashlib
import sys
import uuid
from pathlib import Path

# Add apps/api to path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "apps" / "api"))

from app.config import settings
from app.data_agent.importer import SyntheaImporter
from app.data_agent.models import DataAgentJob
from app.database import async_session_factory


async def import_cohort(csv_dir: Path):
    if not csv_dir.exists():
        print(f"Error: Directory {csv_dir} does not exist.")
        return

    print(f"Connecting to database: {settings.database_url.split('@')[-1]}")
    importer = SyntheaImporter(async_session_factory)

    # Compute quick hash for job tracking
    manifest = "".join(f.name for f in sorted(csv_dir.glob("*.csv")))
    checksum = hashlib.sha256(manifest.encode("utf-8")).hexdigest()

    job = DataAgentJob(
        id=str(uuid.uuid4()),
        source_id="synthea_local_generator",
        status="approved",
        archive_sha256=checksum,
    )

    print(f"Starting import from: {csv_dir}")
    counts = await importer.run(job, csv_dir)
    print("\n--- Import Summary ---")
    for entity, count in counts.items():
        print(f"  {entity}: {count} records imported")
    print("----------------------")


if __name__ == "__main__":
    target_dir = (
        Path(sys.argv[1])
        if len(sys.argv) > 1
        else PROJECT_ROOT / "data" / "raw" / "synthea_output" / "csv"
    )
    asyncio.run(import_cohort(target_dir))
