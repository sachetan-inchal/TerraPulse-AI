from typing import List, Optional, Dict, Any, Literal
from pydantic import BaseModel, Field


TestStatus = Literal["PASS", "PARTIAL", "FAIL", "MOCKED", "BLOCKED", "UNVERIFIED"]


class TestRecord(BaseModel):
    test_id: str
    tab: Literal["COMPONENT", "INTEGRATION", "AGENT", "PROMPT", "AUDIT"]
    component: str
    description: str
    input_data: Dict[str, Any]
    expected_behavior: str
    actual_output: Optional[Any] = None
    execution_evidence: Dict[str, Any] = Field(default_factory=dict)
    dependencies: List[str] = Field(default_factory=list)
    execution_duration_ms: float
    status: TestStatus
    failure_explanation: Optional[str] = None
    recommended_correction: Optional[str] = None
    timestamp: str


class AuditReport(BaseModel):
    report_id: str
    generated_at: str
    total_tests: int
    pass_count: int
    partial_count: int
    fail_count: int
    mocked_count: int
    blocked_count: int
    unverified_count: int
    overall_readiness_score: float  # 0 to 100%
    mock_findings: List[Dict[str, Any]] = Field(default_factory=list)
    api_connectivity: Dict[str, str] = Field(default_factory=dict)
    known_limitations: List[str] = Field(default_factory=list)

