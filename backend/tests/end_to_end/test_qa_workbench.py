import pytest
from qa_engine import QAEngine


@pytest.mark.asyncio
async def test_component_lab_pollutant():
    qa = QAEngine()
    record = await qa.run_component_test("pollutant_identification", {"pollutant": "PM10"})
    assert record.status == "PASS"
    assert record.actual_output["code"] == "PM10"


@pytest.mark.asyncio
async def test_component_lab_geocoding():
    qa = QAEngine()
    record = await qa.run_component_test("geocoding", {"location": "London"})
    assert record.status == "PASS"
    assert "lat" in record.execution_evidence


def test_repository_audit_clean():
    qa = QAEngine()
    audit = qa.run_repository_audit()
    assert audit.mocked_count == 0
    assert audit.overall_readiness_score >= 80.0

