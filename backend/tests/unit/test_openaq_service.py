import pytest
from services.openaq_service import OpenAQService


def test_openaq_service_init():
    service = OpenAQService(api_key="test_dummy_key")
    assert service.api_key == "test_dummy_key"
    assert service.BASE_URL == "https://api.openaq.org/v3"


def test_openaq_headers():
    service = OpenAQService(api_key="test_key_123")
    headers = service._get_headers()
    assert headers["X-API-Key"] == "test_key_123"
    assert headers["Accept"] == "application/json"


def test_missing_api_key_raises():
    service = OpenAQService(api_key="")
    service.api_key = None
    with pytest.raises(ValueError, match="OPENAQ_API_KEY is not configured"):
        service.search_locations()

