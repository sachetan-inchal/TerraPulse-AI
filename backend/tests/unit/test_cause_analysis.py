from services.cause_analysis_service import EnvironmentalCauseAnalysisService


def test_cause_analysis_medical_boundary():
    service = EnvironmentalCauseAnalysisService()
    res = service.analyze(
        location="Urban Basin",
        measurements=[{"parameter": "PM2.5", "value": 85.0}],
        reported_observations=["Coughing", "Throat irritation"]
    )
    assert len(res.ranked_hypotheses) > 0
    assert "NOT a medical diagnosis system" in res.medical_disclaimer
    assert any("Traffic" in h.name for h in res.ranked_hypotheses)


def test_cause_analysis_missing_data_reporting():
    service = EnvironmentalCauseAnalysisService()
    # Missing SO2, CO, meteorology
    res = service.analyze(
        location="Metro",
        measurements=[{"parameter": "PM2.5", "value": 45.0}]
    )
    assert len(res.missing_critical_data) > 0
    assert any("SO2" in item for item in res.missing_critical_data)

