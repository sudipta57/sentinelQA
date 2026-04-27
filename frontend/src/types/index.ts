export type SeverityEnum = "Critical" | "Major" | "Minor";
export type SSEEventType = "tool_call" | "tool_result" | "agent_thought" | "complete" | "error";
export type TestCaseType = "form_validation" | "navigation" | "ui_state" | "error_handling" | "edge_case";
export type PipelineStep =
  | "idle"
  | "crawl_app"
  | "generate_test_cases"
  | "execute_test"
  | "classify_bug"
  | "suggest_fix"
  | "reflect_and_expand"
  | "generate_report"
  | "done"
  | "error";

export interface SSEEvent {
  type: SSEEventType;
  step: string;
  payload: Record<string, unknown> | string | null;
  timestamp: string;
}

export interface ClassifiedBug {
  test_id: string;
  severity: SeverityEnum;
  title: string;
  root_cause_hypothesis: string;
  steps_to_reproduce: string[];
  screenshot_path: string | null;
  error_message: string | null;
  fix_suggestion: string | null;
}

export interface BugsBySeverity {
  critical: ClassifiedBug[];
  major: ClassifiedBug[];
  minor: ClassifiedBug[];
}

export interface Report {
  app_url: string;
  summary: string;
  total_tests: number;
  passed: number;
  failed: number;
  bugs_by_severity: BugsBySeverity;
  recommendations: string[];
  run_duration_ms: number;
}
