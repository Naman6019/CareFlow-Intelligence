"""Create Synthea timeline tables.

Revision ID: 0001_synthea_timeline
Revises:
Create Date: 2026-07-16
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0001_synthea_timeline"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "patients",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("birth_date", sa.Date(), nullable=False),
        sa.Column("death_date", sa.Date(), nullable=True),
        sa.Column("first_name", sa.String(length=120), nullable=False),
        sa.Column("middle_name", sa.String(length=120), nullable=True),
        sa.Column("last_name", sa.String(length=120), nullable=False),
        sa.Column("gender", sa.String(length=20), nullable=True),
        sa.Column("race", sa.String(length=80), nullable=True),
        sa.Column("ethnicity", sa.String(length=80), nullable=True),
        sa.Column("city", sa.String(length=120), nullable=True),
        sa.Column("state", sa.String(length=120), nullable=True),
        sa.Column("postal_code", sa.String(length=20), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_patients_last_name", "patients", ["last_name"])

    op.create_table(
        "encounters",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("patient_id", sa.String(length=36), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("stopped_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("encounter_class", sa.String(length=80), nullable=True),
        sa.Column("code", sa.String(length=80), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(
            ["patient_id"],
            ["patients.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_encounters_patient_started",
        "encounters",
        ["patient_id", "started_at"],
    )

    op.create_table(
        "conditions",
        sa.Column("source_key", sa.String(length=64), nullable=False),
        sa.Column("patient_id", sa.String(length=36), nullable=False),
        sa.Column("encounter_id", sa.String(length=36), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("stopped_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("code_system", sa.String(length=255), nullable=True),
        sa.Column("code", sa.String(length=80), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(
            ["patient_id"],
            ["patients.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("source_key"),
    )
    op.create_index(
        "ix_conditions_patient_started",
        "conditions",
        ["patient_id", "started_at"],
    )

    op.create_table(
        "observations",
        sa.Column("source_key", sa.String(length=64), nullable=False),
        sa.Column("patient_id", sa.String(length=36), nullable=False),
        sa.Column("encounter_id", sa.String(length=36), nullable=True),
        sa.Column("observed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("category", sa.String(length=120), nullable=True),
        sa.Column("code", sa.String(length=80), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("value", sa.Text(), nullable=True),
        sa.Column("units", sa.String(length=80), nullable=True),
        sa.Column("value_type", sa.String(length=80), nullable=True),
        sa.ForeignKeyConstraint(
            ["patient_id"],
            ["patients.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("source_key"),
    )
    op.create_index(
        "ix_observations_patient_observed",
        "observations",
        ["patient_id", "observed_at"],
    )

    op.create_table(
        "medications",
        sa.Column("source_key", sa.String(length=64), nullable=False),
        sa.Column("patient_id", sa.String(length=36), nullable=False),
        sa.Column("encounter_id", sa.String(length=36), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("stopped_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("code", sa.String(length=80), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("reason_code", sa.String(length=80), nullable=True),
        sa.Column("reason_description", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(
            ["patient_id"],
            ["patients.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("source_key"),
    )
    op.create_index(
        "ix_medications_patient_started",
        "medications",
        ["patient_id", "started_at"],
    )

    op.create_table(
        "data_import_runs",
        sa.Column("job_id", sa.String(length=36), nullable=False),
        sa.Column("source_id", sa.String(length=120), nullable=False),
        sa.Column("archive_sha256", sa.String(length=64), nullable=False),
        sa.Column(
            "counts",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
        sa.Column(
            "imported_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("job_id"),
    )
    op.create_index(
        "ix_data_import_runs_archive_sha256",
        "data_import_runs",
        ["archive_sha256"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_data_import_runs_archive_sha256",
        table_name="data_import_runs",
    )
    op.drop_table("data_import_runs")
    op.drop_index(
        "ix_medications_patient_started",
        table_name="medications",
    )
    op.drop_table("medications")
    op.drop_index(
        "ix_observations_patient_observed",
        table_name="observations",
    )
    op.drop_table("observations")
    op.drop_index(
        "ix_conditions_patient_started",
        table_name="conditions",
    )
    op.drop_table("conditions")
    op.drop_index(
        "ix_encounters_patient_started",
        table_name="encounters",
    )
    op.drop_table("encounters")
    op.drop_index("ix_patients_last_name", table_name="patients")
    op.drop_table("patients")

