from pydantic import ValidationError
from schemas.llm import LLMResponse


# Valid final response
final_response = LLMResponse(
    type="final",
    content="Air quality is deteriorating."
)

print(final_response.model_dump())


# Valid tool call
tool_response = LLMResponse(
    type="tool_call",
    tool_name="get_air_quality",
    arguments={"location": "Chennai"}
)

print(tool_response.model_dump())


# Invalid tool call
try:
    invalid_response = LLMResponse(
        type="tool_call",
        content="Air quality is deteriorating."
    )

except ValidationError as e:
    print("Validation failed:")
    print(e)