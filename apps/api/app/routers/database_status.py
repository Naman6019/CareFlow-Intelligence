from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session
from app.db.models import Condition, Encounter, Medication, Observation, Patient

router = APIRouter(prefix="/api/database", tags=["database"])


class DatabaseStatus(BaseModel):
    status: str
    patients: int
    encounters: int
    conditions: int
    observations: int
    medications: int


@router.get("/status", response_model=DatabaseStatus)
async def database_status(
    session: AsyncSession = Depends(get_session),
) -> DatabaseStatus:
    models = [Patient, Encounter, Condition, Observation, Medication]
    counts = [
        await session.scalar(select(func.count()).select_from(model))
        for model in models
    ]
    return DatabaseStatus(
        status="ok",
        patients=counts[0] or 0,
        encounters=counts[1] or 0,
        conditions=counts[2] or 0,
        observations=counts[3] or 0,
        medications=counts[4] or 0,
    )

