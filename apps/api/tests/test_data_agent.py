import csv
import shutil
from pathlib import Path
from zipfile import ZipFile

import pytest

from app.data_agent.models import JobStatus
from app.data_agent.service import DataIntakeAgent
from app.data_agent.store import JobStore
from app.data_agent.tools.download import DownloadResult
from app.data_agent.tools.validate import DatasetValidationTool
from app.data_agent.importer import parse_date, parse_datetime, source_key

CSV_ROWS = {
    "patients.csv": [
        {
            "Id": "patient-1",
            "BIRTHDATE": "1980-01-01",
            "FIRST": "Synthetic",
            "LAST": "Patient",
            "GENDER": "F",
        }
    ],
    "encounters.csv": [
        {
            "Id": "encounter-1",
            "START": "2025-01-01",
            "PATIENT": "patient-1",
            "ENCOUNTERCLASS": "ambulatory",
        }
    ],
    "conditions.csv": [
        {
            "START": "2025-01-01",
            "PATIENT": "patient-1",
            "CODE": "123",
            "DESCRIPTION": "Synthetic condition",
        }
    ],
    "observations.csv": [
        {
            "DATE": "2025-01-01",
            "PATIENT": "patient-1",
            "CODE": "456",
            "VALUE": "120",
            "TYPE": "numeric",
        }
    ],
    "medications.csv": [
        {
            "START": "2025-01-01",
            "PATIENT": "patient-1",
            "CODE": "789",
            "DESCRIPTION": "Synthetic medication",
        }
    ],
}


def build_dataset_archive(root: Path) -> Path:
    csv_root = root / "csv"
    csv_root.mkdir(parents=True)
    for filename, rows in CSV_ROWS.items():
        path = csv_root / filename
        with path.open("w", encoding="utf-8", newline="") as csv_file:
            writer = csv.DictWriter(csv_file, fieldnames=list(rows[0]))
            writer.writeheader()
            writer.writerows(rows)

    archive_path = root / "dataset.zip"
    with ZipFile(archive_path, "w") as archive:
        for path in csv_root.iterdir():
            archive.write(path, arcname=f"csv/{path.name}")
    return archive_path


class FakeDownloadTool:
    def __init__(self, source_archive: Path):
        self.source_archive = source_archive

    async def run(self, source, destination: Path) -> DownloadResult:
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(self.source_archive, destination)
        return DownloadResult(
            path=destination,
            sha256="test-sha256",
            size_bytes=destination.stat().st_size,
        )


def test_validator_accepts_required_synthea_tables(tmp_path: Path) -> None:
    archive = build_dataset_archive(tmp_path)
    validator = DatasetValidationTool(max_extracted_bytes=1_000_000)

    report = validator.run(archive, tmp_path / "extracted")

    assert report.valid is True
    assert report.patient_count == 1
    assert report.row_counts["encounters.csv"] == 1


def test_validator_rejects_zip_path_traversal(tmp_path: Path) -> None:
    archive = tmp_path / "unsafe.zip"
    with ZipFile(archive, "w") as zip_file:
        zip_file.writestr("../patients.csv", "Id\npatient-1\n")

    validator = DatasetValidationTool(max_extracted_bytes=1_000_000)

    with pytest.raises(ValueError, match="unsafe file path"):
        validator.run(archive, tmp_path / "extracted")


@pytest.mark.anyio
async def test_agent_stops_for_human_approval(tmp_path: Path) -> None:
    archive = build_dataset_archive(tmp_path / "fixture")
    store = JobStore(tmp_path / "jobs")
    agent = DataIntakeAgent(
        store=store,
        downloader=FakeDownloadTool(archive),
        validator=DatasetValidationTool(max_extracted_bytes=1_000_000),
    )

    job = agent.create_job("synthea_sample_csv")
    await agent.run(job.id)

    validated_job = agent.get_job(job.id)
    assert validated_job is not None
    assert validated_job.status == JobStatus.AWAITING_APPROVAL
    assert validated_job.report is not None
    assert validated_job.report.patient_count == 1

    approved_job = agent.approve(job.id)
    assert approved_job.status == JobStatus.APPROVED


def test_import_values_are_repeatable() -> None:
    row = {"PATIENT": "patient-1", "CODE": "123", "START": "2025-01-01"}

    assert source_key(row) == source_key(dict(reversed(list(row.items()))))
    assert parse_date("2025-01-01").isoformat() == "2025-01-01"
    assert parse_datetime("2025-01-01T10:30:00Z").tzinfo is not None
