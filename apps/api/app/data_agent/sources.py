from app.config import settings
from app.data_agent.models import DataSource


def get_source_catalog() -> dict[str, DataSource]:
    source = DataSource(
        id="synthea_sample_csv",
        name="Synthea 100-patient CSV sample",
        description=(
            "Official synthetic patient sample published by MITRE's "
            "Synthea project."
        ),
        url=settings.synthea_sample_url,
        publisher="MITRE Synthea",
        license_name="Apache License 2.0",
        format="zip/csv",
        synthetic=True,
        allowed_hosts=["synthetichealth.github.io"],
    )
    return {source.id: source}

