import csv
import hashlib
from collections.abc import Callable, Iterable
from datetime import date, datetime, time, timezone
from pathlib import Path
from typing import Any

from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.data_agent.models import DataAgentJob
from app.db.models import (
    Condition,
    DataImportRun,
    Encounter,
    Medication,
    Observation,
    Patient,
)

CHUNK_SIZE = 1000


def parse_date(value: str) -> date | None:
    return date.fromisoformat(value) if value else None


def parse_datetime(value: str) -> datetime | None:
    if not value:
        return None
    if len(value) == 10:
        return datetime.combine(
            date.fromisoformat(value),
            time.min,
            tzinfo=timezone.utc,
        )
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def source_key(row: dict[str, str]) -> str:
    canonical = "\x1f".join(f"{key}={row.get(key, '')}" for key in sorted(row))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


class SyntheaImporter:
    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
    ):
        self.session_factory = session_factory

    async def run(
        self,
        job: DataAgentJob,
        extraction_dir: Path,
    ) -> dict[str, int]:
        if not job.archive_sha256:
            raise ValueError("Approved job is missing its archive checksum.")

        async with self.session_factory() as session:
            existing = await session.get(DataImportRun, job.id)
            if existing is not None:
                return dict(existing.counts)

            counts = {
                "patients": await self._import_patients(
                    session,
                    self._find_file(extraction_dir, "patients.csv"),
                ),
                "encounters": await self._import_encounters(
                    session,
                    self._find_file(extraction_dir, "encounters.csv"),
                ),
                "conditions": await self._import_events(
                    session,
                    self._find_file(extraction_dir, "conditions.csv"),
                    Condition,
                    self._condition_values,
                ),
                "observations": await self._import_events(
                    session,
                    self._find_file(extraction_dir, "observations.csv"),
                    Observation,
                    self._observation_values,
                ),
                "medications": await self._import_events(
                    session,
                    self._find_file(extraction_dir, "medications.csv"),
                    Medication,
                    self._medication_values,
                ),
            }

            session.add(
                DataImportRun(
                    job_id=job.id,
                    source_id=job.source_id,
                    archive_sha256=job.archive_sha256,
                    counts=counts,
                )
            )
            await session.commit()
            return counts

    async def _import_patients(
        self,
        session: AsyncSession,
        path: Path,
    ) -> int:
        rows = list(self._read_csv(path))
        values = [
            {
                "id": row["Id"],
                "birth_date": parse_date(row["BIRTHDATE"]),
                "death_date": parse_date(row["DEATHDATE"]),
                "first_name": row["FIRST"],
                "middle_name": row["MIDDLE"] or None,
                "last_name": row["LAST"],
                "gender": row["GENDER"] or None,
                "race": row["RACE"] or None,
                "ethnicity": row["ETHNICITY"] or None,
                "city": row["CITY"] or None,
                "state": row["STATE"] or None,
                "postal_code": row["ZIP"] or None,
            }
            for row in rows
        ]
        statement = insert(Patient).values(values)
        await session.execute(
            statement.on_conflict_do_update(
                index_elements=[Patient.id],
                set_={
                    "birth_date": statement.excluded.birth_date,
                    "death_date": statement.excluded.death_date,
                    "first_name": statement.excluded.first_name,
                    "middle_name": statement.excluded.middle_name,
                    "last_name": statement.excluded.last_name,
                    "gender": statement.excluded.gender,
                    "race": statement.excluded.race,
                    "ethnicity": statement.excluded.ethnicity,
                    "city": statement.excluded.city,
                    "state": statement.excluded.state,
                    "postal_code": statement.excluded.postal_code,
                    "updated_at": datetime.now(timezone.utc),
                },
            )
        )
        return len(values)

    async def _import_encounters(
        self,
        session: AsyncSession,
        path: Path,
    ) -> int:
        count = 0
        for batch in self._batched(
            (
                {
                    "id": row["Id"],
                    "patient_id": row["PATIENT"],
                    "started_at": parse_datetime(row["START"]),
                    "stopped_at": parse_datetime(row["STOP"]),
                    "encounter_class": row["ENCOUNTERCLASS"] or None,
                    "code": row["CODE"] or None,
                    "description": row["DESCRIPTION"] or None,
                }
                for row in self._read_csv(path)
            )
        ):
            statement = insert(Encounter).values(batch)
            await session.execute(
                statement.on_conflict_do_update(
                    index_elements=[Encounter.id],
                    set_={
                        "patient_id": statement.excluded.patient_id,
                        "started_at": statement.excluded.started_at,
                        "stopped_at": statement.excluded.stopped_at,
                        "encounter_class": statement.excluded.encounter_class,
                        "code": statement.excluded.code,
                        "description": statement.excluded.description,
                    },
                )
            )
            count += len(batch)
        return count

    async def _import_events(
        self,
        session: AsyncSession,
        path: Path,
        model,
        mapper: Callable[[dict[str, str]], dict[str, Any]],
    ) -> int:
        count = 0
        for batch in self._batched(
            (mapper(row) for row in self._read_csv(path))
        ):
            statement = insert(model).values(batch)
            await session.execute(
                statement.on_conflict_do_nothing(
                    index_elements=[model.source_key],
                )
            )
            count += len(batch)
        return count

    @staticmethod
    def _condition_values(row: dict[str, str]) -> dict[str, Any]:
        return {
            "source_key": source_key(row),
            "patient_id": row["PATIENT"],
            "encounter_id": row["ENCOUNTER"] or None,
            "started_at": parse_datetime(row["START"]),
            "stopped_at": parse_datetime(row["STOP"]),
            "code_system": row["SYSTEM"] or None,
            "code": row["CODE"],
            "description": row["DESCRIPTION"] or None,
        }

    @staticmethod
    def _observation_values(row: dict[str, str]) -> dict[str, Any]:
        return {
            "source_key": source_key(row),
            "patient_id": row["PATIENT"],
            "encounter_id": row["ENCOUNTER"] or None,
            "observed_at": parse_datetime(row["DATE"]),
            "category": row["CATEGORY"] or None,
            "code": row["CODE"],
            "description": row["DESCRIPTION"] or None,
            "value": row["VALUE"] or None,
            "units": row["UNITS"] or None,
            "value_type": row["TYPE"] or None,
        }

    @staticmethod
    def _medication_values(row: dict[str, str]) -> dict[str, Any]:
        return {
            "source_key": source_key(row),
            "patient_id": row["PATIENT"],
            "encounter_id": row["ENCOUNTER"] or None,
            "started_at": parse_datetime(row["START"]),
            "stopped_at": parse_datetime(row["STOP"]),
            "code": row["CODE"],
            "description": row["DESCRIPTION"] or None,
            "reason_code": row["REASONCODE"] or None,
            "reason_description": row["REASONDESCRIPTION"] or None,
        }

    @staticmethod
    def _find_file(root: Path, filename: str) -> Path:
        matches = list(root.rglob(filename))
        if len(matches) != 1:
            raise ValueError(f"Expected exactly one {filename} file.")
        return matches[0]

    @staticmethod
    def _read_csv(path: Path) -> Iterable[dict[str, str]]:
        with path.open("r", encoding="utf-8-sig", newline="") as csv_file:
            yield from csv.DictReader(csv_file)

    @staticmethod
    def _batched(
        rows: Iterable[dict[str, Any]],
        size: int = CHUNK_SIZE,
    ) -> Iterable[list[dict[str, Any]]]:
        batch: list[dict[str, Any]] = []
        for row in rows:
            batch.append(row)
            if len(batch) == size:
                yield batch
                batch = []
        if batch:
            yield batch
