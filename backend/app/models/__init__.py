from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel


class PageElement(BaseModel):
    type: str
    id: str | None = None
    label: str | None = None
    placeholder: str | None = None
    href: str | None = None
    tag: str


class PageInfo(BaseModel):
    url: str
    title: str
    elements: list[PageElement]


class Sitemap(BaseModel):
    pages: list[PageInfo]
    base_url: str


class TestCase(BaseModel):
    id: str
    title: str
    type: Literal["form_validation", "navigation", "ui_state", "error_handling", "edge_case"]
    steps: list[str]
    expected_result: str
    target_element: str | None = None


class TestResult(BaseModel):
    test_id: str
    passed: bool
    error_message: str | None = None
    screenshot_path: str | None = None
    duration_ms: int


class SeverityEnum(str, Enum):
    Critical = "Critical"
    Major = "Major"
    Minor = "Minor"


class ClassifiedBug(BaseModel):
    test_id: str
    severity: SeverityEnum
    title: str
    root_cause_hypothesis: str
    steps_to_reproduce: list[str]
    screenshot_path: str | None = None
    error_message: str | None = None
    fix_suggestion: str | None = None


class BugsBySeverity(BaseModel):
    critical: list[ClassifiedBug]
    major: list[ClassifiedBug]
    minor: list[ClassifiedBug]


class Report(BaseModel):
    app_url: str
    summary: str
    total_tests: int
    passed: int
    failed: int
    bugs_by_severity: BugsBySeverity
    recommendations: list[str]
    run_duration_ms: int


class SSEEventType(str, Enum):
    tool_call = "tool_call"
    tool_result = "tool_result"
    agent_thought = "agent_thought"
    complete = "complete"
    error = "error"


class SSEEvent(BaseModel):
    type: SSEEventType
    step: int
    payload: dict[str, Any]
    timestamp: str


class RunAgentRequest(BaseModel):
    url: str
