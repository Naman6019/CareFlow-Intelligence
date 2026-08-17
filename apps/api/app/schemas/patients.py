from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, Field


class PatientSummary(BaseModel):
    id: str
    first_name: str
    middle_name: str | None
    last_name: str
    birth_date: date
    death_date: date | None
    gender: str | None
    city: str | None
    state: str | None


class PatientListResponse(BaseModel):
    items: list[PatientSummary]
    page: int
    page_size: int
    total: int
    pages: int
    search: str


class PatientStats(BaseModel):
    encounters: int
    conditions: int
    observations: int
    medications: int


class PatientDetail(PatientSummary):
    race: str | None
    ethnicity: str | None
    postal_code: str | None
    stats: PatientStats


class TimelineEvent(BaseModel):
    id: str
    event_type: Literal[
        "encounter",
        "condition",
        "observation",
        "medication",
    ]
    occurred_at: datetime
    ended_at: datetime | None
    category: str | None
    code: str | None
    title: str
    description: str | None
    value: str | None
    units: str | None
    encounter_id: str | None


class PatientTimelineResponse(BaseModel):
    patient_id: str
    events: list[TimelineEvent]
    returned: int
    limit: int = Field(ge=1, le=500)

