from typing import List, Optional, Dict, Any, Literal
from pydantic import BaseModel, Field
from datetime import datetime


class AgentExecutionEvent(BaseModel):
    event_id: str
    timestamp: str
    component: str
    event_type: Literal[
        "USER_REQUEST",
        "LLM_REQUEST",
        "TOOL_SELECTION",
        "TOOL_EXECUTION_START",
        "TOOL_EXECUTION_SUCCESS",
        "TOOL_EXECUTION_ERROR",
        "RETRY",
        "FINAL_RESPONSE",
        "SYSTEM_NOTICE"
    ]
    input_data: Optional[Dict[str, Any]] = None
    output_data: Optional[Dict[str, Any]] = None
    duration_ms: Optional[float] = None
    status: Literal["INFO", "SUCCESS", "WARNING", "ERROR"] = "INFO"
    error_details: Optional[str] = None


class AgentRunResult(BaseModel):
    run_id: str
    user_prompt: str
    final_answer: str
    iterations: int
    total_duration_ms: float
    events: List[AgentExecutionEvent] = Field(default_factory=list)
    tools_called: List[str] = Field(default_factory=list)
    map_features: Optional[Dict[str, Any]] = None  # GeoJSON FeatureCollection
    research_citations: List[Dict[str, Any]] = Field(default_factory=list)
    environmental_data: Optional[Dict[str, Any]] = None
    confidence_assessment: Optional[str] = None
    uncertainty_notes: List[str] = Field(default_factory=list)

