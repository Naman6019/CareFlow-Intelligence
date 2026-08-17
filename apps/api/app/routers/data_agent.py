from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, HTTPException, status

from app.config import settings
from app.data_agent.models import (
    CreateDataJobRequest,
    DataAgentJob,
    DataSourceList,
    JobStatus,
)
from app.data_agent.service import DataIntakeAgent
from app.data_agent.importer import SyntheaImporter
from app.data_agent.sources import get_source_catalog
from app.data_agent.store import JobStore
from app.data_agent.tools.download import OfficialDatasetDownloadTool
from app.data_agent.tools.validate import DatasetValidationTool
from app.database import async_session_factory

router = APIRouter(prefix="/api/data-agent", tags=["data-agent"])

store = JobStore(settings.data_dir / "intake")
agent = DataIntakeAgent(
    store=store,
    downloader=OfficialDatasetDownloadTool(
        max_bytes=settings.agent_max_download_bytes,
    ),
    validator=DatasetValidationTool(
        max_extracted_bytes=settings.agent_max_extracted_bytes,
    ),
    importer=SyntheaImporter(async_session_factory),
)


@router.get("/sources", response_model=DataSourceList)
async def list_sources() -> DataSourceList:
    return DataSourceList(sources=list(get_source_catalog().values()))


@router.post(
    "/jobs",
    response_model=DataAgentJob,
    status_code=status.HTTP_202_ACCEPTED,
)
async def create_job(
    request: CreateDataJobRequest,
    background_tasks: BackgroundTasks,
) -> DataAgentJob:
    try:
        job = agent.create_job(request.source_id)
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error

    background_tasks.add_task(agent.run, job.id)
    return job


@router.get("/jobs/{job_id}", response_model=DataAgentJob)
async def get_job(job_id: UUID) -> DataAgentJob:
    job = agent.get_job(str(job_id))
    if job is None:
        raise HTTPException(status_code=404, detail="Data agent job not found.")
    return job


@router.post("/jobs/{job_id}/approve", response_model=DataAgentJob)
async def approve_job(job_id: UUID) -> DataAgentJob:
    try:
        return agent.approve(str(job_id))
    except LookupError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    except ValueError as error:
        raise HTTPException(status_code=409, detail=str(error)) from error


@router.post(
    "/jobs/{job_id}/import",
    response_model=DataAgentJob,
    status_code=status.HTTP_202_ACCEPTED,
)
async def import_job(
    job_id: UUID,
    background_tasks: BackgroundTasks,
) -> DataAgentJob:
    try:
        job = agent.start_import(str(job_id))
    except LookupError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    except (RuntimeError, ValueError) as error:
        raise HTTPException(status_code=409, detail=str(error)) from error

    if job.status == JobStatus.IMPORTING:
        background_tasks.add_task(agent.run_import, job.id)
    return job
