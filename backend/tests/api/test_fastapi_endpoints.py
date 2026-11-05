from fastapi.testclient import TestClient
from main import app

client = TestClient(app)


def test_health_endpoint():
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"


def test_pollutant_endpoint():
    response = client.get("/api/pollutant/PM2.5")
    assert response.status_code == 200
    data = response.json()
    assert data["code"] == "PM2.5"
    assert data["is_known_pollutant"] is True


def test_pollutant_compare_endpoint():
    response = client.post("/api/pollutant/compare", json={"pollutants": ["PM2.5", "O3"]})
    assert response.status_code == 200
    data = response.json()
    assert "secondary_pollutants" in data


def test_qa_workbench_html_served():
    response = client.get("/workbench")
    assert response.status_code == 200
    assert "TerraPulse AIR" in response.text
    assert "Component Lab" in response.text


def test_qa_audit_endpoint():
    response = client.get("/api/qa/audit")
    assert response.status_code == 200
    data = response.json()
    assert "overall_readiness_score" in data
    assert "mock_findings" in data

