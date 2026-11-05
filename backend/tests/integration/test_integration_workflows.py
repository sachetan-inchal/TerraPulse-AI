import pytest
from qa_engine import QAEngine


@pytest.mark.asyncio
async def test_integration_scenario_int01():
    qa = QAEngine()
    record = await qa.run_integration_test("INT-01")
    assert record.status in ["PASS", "PARTIAL"]
    assert record.execution_duration_ms > 0
    assert "stage_1_pollutant_intelligence" in record.actual_output


@pytest.mark.asyncio
async def test_integration_scenario_int03():
    qa = QAEngine()
    record = await qa.run_integration_test("INT-03")
    assert record.status == "PASS"
    assert "stage_1_cause_analysis" in record.actual_output
    assert "stage_2_geospatial_buffer" in record.actual_output

