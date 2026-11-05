from schemas.llm import LLMResponse


final_response = LLMResponse(
    type="final",
    content="Air quality is deteriorating."
)

tool_response = LLMResponse(
    type="tool_call",
    tool_name="get_air_quality",
    arguments={
        "location": "Chennai",
        "pollutant": "PM2.5"
    }
)

print(final_response.model_dump())
print(tool_response.model_dump())