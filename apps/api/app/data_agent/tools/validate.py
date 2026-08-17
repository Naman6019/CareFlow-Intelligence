import csv
import shutil
from pathlib import Path, PurePosixPath
from zipfile import BadZipFile, ZipFile, is_zipfile

from app.data_agent.models import DatasetReport

REQUIRED_SCHEMAS: dict[str, set[str]] = {
    "patients.csv": {"Id", "BIRTHDATE", "FIRST", "LAST", "GENDER"},
    "encounters.csv": {"Id", "START", "PATIENT", "ENCOUNTERCLASS"},
    "conditions.csv": {"START", "PATIENT", "CODE", "DESCRIPTION"},
    "observations.csv": {"DATE", "PATIENT", "CODE", "VALUE", "TYPE"},
    "medications.csv": {"START", "PATIENT", "CODE", "DESCRIPTION"},
}


class DatasetValidationTool:
    """Safely extract and validate the required Synthea CSV tables."""

    def __init__(self, max_extracted_bytes: int):
        self.max_extracted_bytes = max_extracted_bytes

    def run(self, archive_path: Path, extraction_dir: Path) -> DatasetReport:
        if not is_zipfile(archive_path):
            raise ValueError("Downloaded artifact is not a valid ZIP archive.")

        extraction_dir.mkdir(parents=True, exist_ok=True)

        try:
            with ZipFile(archive_path) as archive:
                self._validate_archive(archive)
                self._extract_csv_files(archive, extraction_dir)
        except BadZipFile as error:
            raise ValueError("Downloaded artifact is not a valid ZIP archive.") from error

        discovered: dict[str, list[Path]] = {}
        for path in extraction_dir.rglob("*.csv"):
            discovered.setdefault(path.name.lower(), []).append(path)

        missing = [
            name for name in REQUIRED_SCHEMAS if name not in discovered
        ]
        if missing:
            raise ValueError(
                f"Dataset is missing required files: {', '.join(missing)}"
            )

        duplicates = [
            name for name, paths in discovered.items() if len(paths) > 1
        ]
        if duplicates:
            raise ValueError(
                f"Dataset contains duplicate CSV names: {', '.join(duplicates)}"
            )

        row_counts: dict[str, int] = {}
        for filename, required_columns in REQUIRED_SCHEMAS.items():
            path = discovered[filename][0]
            row_counts[filename] = self._validate_csv(
                path,
                required_columns,
            )

        patient_ids = self._read_column(
            discovered["patients.csv"][0],
            "Id",
        )
        if not patient_ids:
            raise ValueError("patients.csv does not contain any patients.")

        for filename in REQUIRED_SCHEMAS:
            if filename == "patients.csv":
                continue
            referenced_ids = self._read_column(
                discovered[filename][0],
                "PATIENT",
            )
            unknown_ids = referenced_ids - patient_ids
            if unknown_ids:
                raise ValueError(
                    f"{filename} references unknown patient identifiers."
                )

        return DatasetReport(
            valid=True,
            patient_count=len(patient_ids),
            row_counts=row_counts,
            files=sorted(discovered),
            warnings=[],
        )

    def _validate_archive(self, archive: ZipFile) -> None:
        total_size = 0
        for member in archive.infolist():
            member_path = PurePosixPath(member.filename)
            if member_path.is_absolute() or ".." in member_path.parts:
                raise ValueError("ZIP archive contains an unsafe file path.")
            total_size += member.file_size
            if total_size > self.max_extracted_bytes:
                raise ValueError("ZIP archive exceeds the extraction size limit.")

    def _extract_csv_files(self, archive: ZipFile, extraction_dir: Path) -> None:
        root = extraction_dir.resolve()
        for member in archive.infolist():
            if member.is_dir() or not member.filename.lower().endswith(".csv"):
                continue

            relative_path = Path(*PurePosixPath(member.filename).parts)
            destination = (root / relative_path).resolve()
            if not destination.is_relative_to(root):
                raise ValueError("ZIP archive contains an unsafe file path.")

            destination.parent.mkdir(parents=True, exist_ok=True)
            with archive.open(member) as source, destination.open("wb") as output:
                shutil.copyfileobj(source, output)

    @staticmethod
    def _validate_csv(path: Path, required_columns: set[str]) -> int:
        with path.open("r", encoding="utf-8-sig", newline="") as csv_file:
            reader = csv.DictReader(csv_file)
            columns = set(reader.fieldnames or [])
            missing_columns = required_columns - columns
            if missing_columns:
                missing = ", ".join(sorted(missing_columns))
                raise ValueError(f"{path.name} is missing columns: {missing}")
            return sum(1 for _ in reader)

    @staticmethod
    def _read_column(path: Path, column: str) -> set[str]:
        values: set[str] = set()
        with path.open("r", encoding="utf-8-sig", newline="") as csv_file:
            reader = csv.DictReader(csv_file)
            for row in reader:
                value = row.get(column, "").strip()
                if value:
                    values.add(value)
        return values

