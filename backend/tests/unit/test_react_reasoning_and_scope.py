import pytest
import json
from qa_engine import QAEngine
from agent.geographic_scope import GeographicScopeAnalyzer
from agent.orchestrator import ReActAgent


def test_geographic_scope_analyzer_usa():
    res = GeographicScopeAnalyzer.analyze("Find emission sources in USA.")
    assert res["scope_type"] == "COUNTRY"
    assert res["target_name"] == "USA"
    assert res["objective_type"] == "EMISSION_SOURCES"
    assert "Never silently substitute a single city" in res["strict_rule"] or "radius limitations" in res["strict_rule"]


def test_geographic_scope_analyzer_california():
    res = GeographicScopeAnalyzer.analyze("Find emission sources in California.")
    assert res["scope_type"] == "STATE_PROVINCE"
    assert res["target_name"] == "California"
    assert res["objective_type"] == "EMISSION_SOURCES"
    assert "state-level" in res["strict_rule"].lower()


def test_geographic_scope_analyzer_rvce():
    res = GeographicScopeAnalyzer.analyze("Find emission sources near RVCE.")
    assert res["scope_type"] == "LOCAL"
    assert "RV College" in res["target_name"] or "rvce" in res["target_name"].lower()
    assert res["objective_type"] == "EMISSION_SOURCES"
    assert "Do NOT automatically call OpenAQ" in res["strict_rule"]


@pytest.mark.asyncio
async def test_scenario_4_empty_emission_search_non_absence():
    qa = QAEngine()
    record = await qa.run_agent_test(23)
    assert record.status == "PASS"
    obs_eval = record.actual_output["observation_evaluation"]
    assert "does not prove" in obs_eval.lower()
    assert record.actual_output["synthesis"]["stopping_recommendation"] == "INCONCLUSIVE_NO_INDEXED_SOURCES"


@pytest.mark.asyncio
async def test_scenario_5_stations_vs_sources_disambiguation():
    qa = QAEngine()
    record = await qa.run_agent_test(24)
    assert record.status == "PASS"
    obs_eval = record.actual_output["observation_evaluation"]
    assert "not emission sources" in obs_eval.lower()
    assert record.actual_output["synthesis"]["stopping_recommendation"] == "INSUFFICIENT_EVIDENCE_STATIONS_WITHOUT_MEASUREMENTS"


@pytest.mark.asyncio
async def test_scenario_6_tool_failure_and_fallback():
    qa = QAEngine()
    record = await qa.run_agent_test(25)
    assert record.status == "PASS"
    obs_eval = record.actual_output["observation_evaluation"]
    assert "fallback" in obs_eval.lower() or "alternative tool" in obs_eval.lower()


@pytest.mark.asyncio
async def test_scenario_7_exhausted_searches_inconclusive():
    qa = QAEngine()
    record = await qa.run_agent_test(26)
    assert record.status == "PASS"
    assert record.actual_output["synthesis"]["stopping_recommendation"] == "INCONCLUSIVE_ALL_SEARCHES_EXHAUSTED"


@pytest.mark.asyncio
async def test_scenario_1_usa_scope_recognition():
    qa = QAEngine()
    record = await qa.run_agent_test(20)
    assert record.status == "PASS"
    assert record.execution_duration_ms > 0
    ans = record.actual_output.get("final_answer_preview", "").lower()
    assert any(w in ans for w in ["nationwide", "country", "united states", "usa", "national"])


@pytest.mark.asyncio
async def test_scenario_2_california_scope_recognition():
    qa = QAEngine()
    record = await qa.run_agent_test(21)
    assert record.status == "PASS"
    assert record.execution_duration_ms > 0
    ans = record.actual_output.get("final_answer_preview", "").lower()
    assert "california" in ans or "state" in ans


@pytest.mark.asyncio
async def test_scenario_3_rvce_local_source_discovery():
    qa = QAEngine()
    record = await qa.run_agent_test(22)
    assert record.status == "PASS"
    assert record.execution_duration_ms > 0
    ans = record.actual_output.get("final_answer_preview", "").lower()
    assert any(w in ans for w in ["rvce", "college", "bengaluru", "candidate", "facility", "sources", "proximity"])


def test_coverage_spec_includes_all_new_tests():
    qa = QAEngine()
    spec = qa.COVERAGE_SPEC
    agent_tests = spec["Agent Orchestrator & Stopping Policy"]["tests"]
    for i in range(20, 27):
        assert f"TC-{i:02d}" in agent_tests

    prompt_tests = spec["Prompt Arena Acceptance Suite"]["tests"]
    for i in range(29, 36):
        assert f"P{i:02d}" in prompt_tests


