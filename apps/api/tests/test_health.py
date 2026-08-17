from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health_reports_synthetic_non_clinical_mode() -> None:
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "service": "CareFlow Intelligence API",
        "version": "0.5.0",
        "data_mode": "synthetic",
        "clinical_use": False,
    }


def test_data_agent_lists_only_approved_sources() -> None:
    response = client.get("/api/data-agent/sources")

    assert response.status_code == 200
    assert response.json()["sources"][0]["id"] == "synthea_sample_csv"
    assert response.json()["sources"][0]["synthetic"] is True
