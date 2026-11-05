import pytest
from pydantic import ValidationError
from schemas.llm import LLMResponse


def test_valid_final_response():
    response = LLMResponse(
        type="final",
        content="Air quality is deteriorating."
    )
    assert response.type == "final"
    assert response.content == "Air quality is deteriorating."


def test_valid_tool_call():
    response = LLMResponse(
        type="tool_call",
        tool_name="get_air_quality",
        arguments={"location": "Chennai"}
    )
    assert response.type == "tool_call"
    assert response.tool_name == "get_air_quality"


def test_tool_call_without_name_fails():
    with pytest.raises(ValidationError):
        LLMResponse(
            type="tool_call",
            content=None
        )