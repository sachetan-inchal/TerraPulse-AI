from typing import Literal, Any
from pydantic import BaseModel, Field, ConfigDict, model_validator


class LLMResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")
    type: Literal["final", "tool_call"]
    content: str | None = None
    tool_name: str | None = None
    arguments: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_response(self):
        if self.type == "final":
            if not self.content:
                raise ValueError("Final response must contain content")
            if self.tool_name is not None:
                raise ValueError("Final response cannot contain a tool name")

        elif self.type == "tool_call":
            if not self.tool_name:
                raise ValueError("Tool call must contain a tool name")
            if self.content is not None:
                raise ValueError("Tool call cannot contain final content")

        return self