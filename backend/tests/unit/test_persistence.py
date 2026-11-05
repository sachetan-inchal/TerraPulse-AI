from services.storage_service import StorageService


def test_storage_fallback_and_redaction():
    storage = StorageService()
    status = storage.get_status()
    assert "fallback_active" in status

    # Verify credential redaction
    test_id = "test_sess_redact"
    storage.save_session(test_id, {
        "api_key": "secret_abc_123",
        "nested": {"token": "my_secret_token", "normal": "public_data"}
    })

    retrieved = storage.get_session(test_id)
    assert retrieved is not None
    assert retrieved["api_key"] == "[REDACTED_CREDENTIAL]"
    assert retrieved["nested"]["token"] == "[REDACTED_CREDENTIAL]"
    assert retrieved["nested"]["normal"] == "public_data"

