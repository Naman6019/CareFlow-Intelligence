import math
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import (
    DateTime,
    String,
    Text,
    cast,
    func,
    literal,
    null,
    or_,
    select,
    union_all,
)
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session
from app.db.models import Condition, Encounter, Medication, Observation, Patient
from app.schemas.patients import (
    PatientDetail,
    PatientListResponse,
    PatientStats,
    PatientSummary,
    PatientTimelineResponse,
    TimelineEvent,
)

router = APIRouter(prefix="/api/patients", tags=["patients"])


def patient_summary(patient: Patient) -> PatientSummary:
    return PatientSummary(
        id=patient.id,
        first_name=patient.first_name,
        middle_name=patient.middle_name,
        last_name=patient.last_name,
        birth_date=patient.birth_date,
        death_date=patient.death_date,
        gender=patient.gender,
        city=patient.city,
        state=patient.state,
    )


@router.get("", response_model=PatientListResponse)
async def list_patients(
    search: str = Query(default="", max_length=100),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    session: AsyncSession = Depends(get_session),
) -> PatientListResponse:
    search = search.strip()
    filters = []
    if search:
        pattern = f"%{search}%"
        filters.append(
            or_(
                Patient.first_name.ilike(pattern),
                Patient.last_name.ilike(pattern),
                Patient.city.ilike(pattern),
                Patient.state.ilike(pattern),
                Patient.id.ilike(pattern),
            )
        )

    total_statement = select(func.count()).select_from(Patient)
    patient_statement = select(Patient)
    if filters:
        total_statement = total_statement.where(*filters)
        patient_statement = patient_statement.where(*filters)

    total = await session.scalar(total_statement) or 0
    patients = (
        await session.scalars(
            patient_statement
            .order_by(Patient.last_name, Patient.first_name)
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
    ).all()

    return PatientListResponse(
        items=[patient_summary(patient) for patient in patients],
        page=page,
        page_size=page_size,
        total=total,
        pages=math.ceil(total / page_size) if total else 0,
        search=search,
    )


@router.get("/{patient_id}", response_model=PatientDetail)
async def get_patient(
    patient_id: UUID,
    session: AsyncSession = Depends(get_session),
) -> PatientDetail:
    patient = await session.get(Patient, str(patient_id))
    if patient is None:
        raise HTTPException(status_code=404, detail="Patient not found.")

    counts = []
    for model in (Encounter, Condition, Observation, Medication):
        counts.append(
            await session.scalar(
                select(func.count())
                .select_from(model)
                .where(model.patient_id == patient.id)
            )
            or 0
        )

    return PatientDetail(
        **patient_summary(patient).model_dump(),
        race=patient.race,
        ethnicity=patient.ethnicity,
        postal_code=patient.postal_code,
        stats=PatientStats(
            encounters=counts[0],
            conditions=counts[1],
            observations=counts[2],
            medications=counts[3],
        ),
    )


@router.get(
    "/{patient_id}/timeline",
    response_model=PatientTimelineResponse,
)
async def get_patient_timeline(
    patient_id: UUID,
    limit: int = Query(default=200, ge=1, le=500),
    session: AsyncSession = Depends(get_session),
) -> PatientTimelineResponse:
    patient_key = str(patient_id)
    if await session.get(Patient, patient_key) is None:
        raise HTTPException(status_code=404, detail="Patient not found.")

    null_datetime = cast(null(), DateTime(timezone=True))
    null_string = cast(null(), String)
    null_text = cast(null(), Text)

    encounters = select(
        Encounter.id.label("id"),
        literal("encounter").label("event_type"),
        Encounter.started_at.label("occurred_at"),
        Encounter.stopped_at.label("ended_at"),
        Encounter.encounter_class.label("category"),
        Encounter.code.label("code"),
        func.coalesce(Encounter.description, "Encounter").label("title"),
        null_text.label("description"),
        null_text.label("value"),
        null_string.label("units"),
        Encounter.id.label("encounter_id"),
    ).where(Encounter.patient_id == patient_key)

    conditions = select(
        Condition.source_key.label("id"),
        literal("condition").label("event_type"),
        Condition.started_at.label("occurred_at"),
        Condition.stopped_at.label("ended_at"),
        literal("condition").label("category"),
        Condition.code.label("code"),
        func.coalesce(Condition.description, "Condition").label("title"),
        Condition.code_system.label("description"),
        null_text.label("value"),
        null_string.label("units"),
        Condition.encounter_id.label("encounter_id"),
    ).where(Condition.patient_id == patient_key)

    observations = select(
        Observation.source_key.label("id"),
        literal("observation").label("event_type"),
        Observation.observed_at.label("occurred_at"),
        null_datetime.label("ended_at"),
        Observation.category.label("category"),
        Observation.code.label("code"),
        func.coalesce(Observation.description, "Observation").label("title"),
        Observation.value_type.label("description"),
        Observation.value.label("value"),
        Observation.units.label("units"),
        Observation.encounter_id.label("encounter_id"),
    ).where(Observation.patient_id == patient_key)

    medications = select(
        Medication.source_key.label("id"),
        literal("medication").label("event_type"),
        Medication.started_at.label("occurred_at"),
        Medication.stopped_at.label("ended_at"),
        literal("medication").label("category"),
        Medication.code.label("code"),
        func.coalesce(Medication.description, "Medication").label("title"),
        Medication.reason_description.label("description"),
        null_text.label("value"),
        null_string.label("units"),
        Medication.encounter_id.label("encounter_id"),
    ).where(Medication.patient_id == patient_key)

    timeline = union_all(
        encounters,
        conditions,
        observations,
        medications,
    ).subquery("patient_timeline")

    rows = (
        await session.execute(
            select(timeline)
            .order_by(timeline.c.occurred_at.desc(), timeline.c.id)
            .limit(limit)
        )
    ).mappings()

    events = [TimelineEvent.model_validate(row) for row in rows]
    return PatientTimelineResponse(
        patient_id=patient_key,
        events=events,
        returned=len(events),
        limit=limit,
    )

