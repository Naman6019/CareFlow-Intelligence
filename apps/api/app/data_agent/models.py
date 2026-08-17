from datetime import datetime, timezone
from enum import StrEnum

from pydantic import BaseModel, Field


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class JobStatus(StrEnum):
    QUEUED = "queued"
    DOWNLOADING = "downloading"
    VALIDATING = "validating"
    AWAITING_APPROVAL = "awaiting_approval"
    APPROVED = "approved"
    IMPORTING = "importing"
    IMPORTED = "imported"
    FAILED = "failed"


class DataSource(BaseModel):
    id: str
    name: str
    description: str
    url: str
    publisher: str
    license_name: str
    format: str
    synthetic: bool
    allowed_hosts: list[str]


class AgentEvent(BaseModel):
    occurred_at: datetime = Field(default_factory=utc_now)
    step: str
    status: str
    message: str


class DatasetReport(BaseModel):
    valid: bool
    patient_count: int
    row_counts: dict[str, int]
    files: list[str]
    warnings: list[str] = Field(default_factory=list)


class DataAgentJob(BaseModel):
    id: str
    source_id: str
    status: JobStatus
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)
    approved_at: datetime | None = None
    archive_sha256: str | None = None
    archive_size_bytes: int | None = None
    report: DatasetReport | None = None
    import_counts: dict[str, int] | None = None
    error: str | None = None
    trace: list[AgentEvent] = Field(default_factory=list)


class CreateDataJobRequest(BaseModel):
    source_id: str = "synthea_sample_csv"


class DataSourceList(BaseModel):
    sources: list[DataSource]
