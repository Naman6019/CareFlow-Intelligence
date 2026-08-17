from app.data_agent.models import AgentEvent, DataAgentJob, JobStatus, utc_now
from app.data_agent.importer import SyntheaImporter
from app.data_agent.sources import get_source_catalog
from app.data_agent.store import JobStore
from app.data_agent.tools.download import OfficialDatasetDownloadTool
from app.data_agent.tools.validate import DatasetValidationTool


class DataIntakeAgent:
    """Run a bounded acquire-validate-review workflow for synthetic datasets."""

    def __init__(
        self,
        store: JobStore,
        downloader: OfficialDatasetDownloadTool,
        validator: DatasetValidationTool,
        importer: SyntheaImporter | None = None,
    ):
        self.store = store
        self.downloader = downloader
        self.validator = validator
        self.importer = importer
        self.sources = get_source_catalog()

    def create_job(self, source_id: str) -> DataAgentJob:
        if source_id not in self.sources:
            raise ValueError("Unknown or unapproved dataset source.")
        return self.store.create(source_id)

    def get_job(self, job_id: str) -> DataAgentJob | None:
        return self.store.get(job_id)

    async def run(self, job_id: str) -> None:
        job = self._required_job(job_id)
        source = self.sources[job.source_id]
        job_directory = self.store.job_directory(job.id)

        try:
            job.status = JobStatus.DOWNLOADING
            job.trace.append(
                AgentEvent(
                    step="download",
                    status="started",
                    message=f"Downloading from approved host {source.allowed_hosts[0]}.",
                )
            )
            self.store.save(job)

            download = await self.downloader.run(
                source,
                job_directory / "source.zip",
            )
            job.archive_sha256 = download.sha256
            job.archive_size_bytes = download.size_bytes
            job.trace.append(
                AgentEvent(
                    step="download",
                    status="completed",
                    message=f"Downloaded {download.size_bytes} bytes.",
                )
            )

            job.status = JobStatus.VALIDATING
            job.trace.append(
                AgentEvent(
                    step="validate",
                    status="started",
                    message="Checking ZIP safety, CSV schemas, and patient references.",
                )
            )
            self.store.save(job)

            job.report = self.validator.run(
                download.path,
                job_directory / "extracted",
            )
            job.status = JobStatus.AWAITING_APPROVAL
            job.trace.append(
                AgentEvent(
                    step="validate",
                    status="completed",
                    message=(
                        f"Validated {job.report.patient_count} synthetic patients; "
                        "human approval is required before import."
                    ),
                )
            )
            self.store.save(job)
        except Exception as error:
            job.status = JobStatus.FAILED
            job.error = str(error)
            job.trace.append(
                AgentEvent(
                    step="agent",
                    status="failed",
                    message=str(error),
                )
            )
            self.store.save(job)

    def approve(self, job_id: str) -> DataAgentJob:
        job = self._required_job(job_id)
        if job.status != JobStatus.AWAITING_APPROVAL:
            raise ValueError("Only validated jobs can be approved.")

        job.status = JobStatus.APPROVED
        job.approved_at = utc_now()
        job.trace.append(
            AgentEvent(
                step="approval",
                status="completed",
                message="Dataset approved for the future database import step.",
            )
        )
        return self.store.save(job)

    def start_import(self, job_id: str) -> DataAgentJob:
        job = self._required_job(job_id)
        if self.importer is None:
            raise RuntimeError("Database importer is not configured.")
        if job.status == JobStatus.IMPORTED:
            return job
        if job.status != JobStatus.APPROVED:
            raise ValueError("Only approved jobs can be imported.")

        job.status = JobStatus.IMPORTING
        job.error = None
        job.trace.append(
            AgentEvent(
                step="import",
                status="started",
                message="Importing validated timeline data into PostgreSQL.",
            )
        )
        return self.store.save(job)

    async def run_import(self, job_id: str) -> None:
        job = self._required_job(job_id)
        if self.importer is None:
            raise RuntimeError("Database importer is not configured.")

        try:
            job.import_counts = await self.importer.run(
                job,
                self.store.job_directory(job.id) / "extracted",
            )
            job.status = JobStatus.IMPORTED
            job.trace.append(
                AgentEvent(
                    step="import",
                    status="completed",
                    message="Validated synthetic timeline data imported.",
                )
            )
            self.store.save(job)
        except Exception as error:
            job.status = JobStatus.FAILED
            job.error = str(error)
            job.trace.append(
                AgentEvent(
                    step="import",
                    status="failed",
                    message=str(error),
                )
            )
            self.store.save(job)

    def _required_job(self, job_id: str) -> DataAgentJob:
        job = self.store.get(job_id)
        if job is None:
            raise LookupError("Data agent job was not found.")
        return job
