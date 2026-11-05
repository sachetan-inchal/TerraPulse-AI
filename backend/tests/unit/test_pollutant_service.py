from services.pollutant_service import PollutantService


def test_known_pollutant_pm25():
    service = PollutantService()
    profile = service.get_pollutant_profile("PM2.5")
    assert profile.code == "PM2.5"
    assert profile.is_known_pollutant is True
    assert "Primary and Secondary" in profile.pollutant_type
    assert profile.standards.who_24h_limit is not None
    assert "not intended as a medical diagnosis" in profile.health_effects.medical_disclaimer.lower()


def test_unknown_pollutant_xyz927_not_invented():
    service = PollutantService()
    profile = service.get_pollutant_profile("XYZ-927")
    assert profile.is_known_pollutant is False
    assert "Verification failed" in profile.verification_notes
    assert profile.standards.who_annual_limit is None
    assert profile.standards.who_24h_limit is None


def test_pollutant_comparison():
    service = PollutantService()
    comp = service.compare_pollutants(["PM2.5", "O3", "CO"])
    assert "O3" in comp["secondary_pollutants"]
    assert "CO" in comp["primary_pollutants"]
    assert len(comp["profiles"]) == 3
