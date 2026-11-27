from typing import Any, Literal, Optional, TypedDict
from pydantic import BaseModel, Field


class SpecArtifact(BaseModel):
    feature_name: str = Field(..., min_length=1)
    requirements: list[str] = Field(..., min_length=1)
    test_cases: list[str] = Field(..., min_length=1)
    interfaces: str = Field(..., min_length=1)


class CodeArtifact(BaseModel):
    implementation_code: str = Field(..., min_length=1)
    test_code: str = Field(..., min_length=1)
    iteration: int = Field(..., ge=1)


class QAReport(BaseModel):
    tests_passed: bool
    total_tests: int = Field(..., ge=0)
    failed_tests: int = Field(..., ge=0)
    execution_output: str
    review_feedback: list[str] = Field(default_factory=list)
    status: Literal["PASSED", "NEEDS_REVISION", "MAX_CYCLES_EXCEEDED"]


class SquadState(TypedDict, total=False):
    user_request: str
    spec: Optional[SpecArtifact]
    code: Optional[CodeArtifact]
    qa_report: Optional[QAReport]
    iteration: int
    max_iterations: int
    inject_bug: bool
    timeline: list[dict[str, Any]]
