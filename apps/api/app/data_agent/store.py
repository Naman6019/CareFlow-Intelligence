from pathlib import Path
from uuid import UUID, uuid4

from app.data_agent.models import (
    AgentEvent,
    DataAgentJob,
    JobStatus,
    utc_now,
)


class JobStore:
    def __init__(self, root: Path):
        self.root = root

    def create(self, source_id: str) -> DataAgentJob:
        job = DataAgentJob(
            id=str(uuid4()),
            source_id=source_id,
            status=JobStatus.QUEUED,
            trace=[
                AgentEvent(
                    step="plan",
                    status="completed",
                    message="Approved source selected; acquisition queued.",
                )
            ],
        )
        return self.save(job)

    def get(self, job_id: str) -> DataAgentJob | None:
        path = self._job_path(job_id)
        if not path.exists():
            return None
        return DataAgentJob.model_validate_json(path.read_text(encoding="utf-8"))

    def save(self, job: DataAgentJob) -> DataAgentJob:
        job.updated_at = utc_now()
        path = self._job_path(job.id)
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary_path = path.with_suffix(".tmp")
        temporary_path.write_text(
            job.model_dump_json(indent=2),
            encoding="utf-8",
        )
        temporary_path.replace(path)
        return job

    def job_directory(self, job_id: str) -> Path:
        canonical_id = str(UUID(job_id))
        return self.root / canonical_id

    def _job_path(self, job_id: str) -> Path:
        return self.job_directory(job_id) / "job.json"

