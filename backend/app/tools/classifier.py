import logging

import google.generativeai as genai

from app.config import get_settings
from app.models import ClassifiedBug, SeverityEnum, TestCase, TestResult
from app.utils.json_parser import parse_gemini_json

logger = logging.getLogger(__name__)


async def call_gemini_with_retry(model, prompt: str, max_retries: int = 3) -> str:
    """Call Gemini with exponential backoff on rate limit or server errors."""
    import asyncio as _asyncio

    last_error = None
    for attempt in range(max_retries):
        try:
            response = await _asyncio.to_thread(model.generate_content, prompt)
            return response.text
        except Exception as e:
            last_error = e
            error_str = str(e).lower()
            if any(x in error_str for x in ["429", "quota", "rate_limit", "resource_exhausted", "500", "503"]):
                wait_seconds = (2 ** attempt) * 3  # 3s, 6s, 12s
                logger.warning(
                    f"Gemini API error attempt {attempt+1}/{max_retries}: {e}. Retrying in {wait_seconds}s..."
                )
                await _asyncio.sleep(wait_seconds)
                continue
            raise
    raise last_error


def _build_prompt(test_case: TestCase, result: TestResult) -> str:
    steps_text = "\n".join(
        f"    {i + 1}. {step}" for i, step in enumerate(test_case.steps)
    )

    return (
        "You are a senior QA engineer performing bug triage. A test case has failed during automated testing of a web application. Analyse the failure and classify it.\n"
        "\n"
        "TEST CASE DETAILS:\n"
        f"  ID: {test_case.id}\n"
        f"  Title: {test_case.title}\n"
        f"  Type: {test_case.type}\n"
        "  Steps executed:\n"
        f"{steps_text}\n"
        f"  Expected result: {test_case.expected_result}\n"
        "\n"
        "ACTUAL FAILURE:\n"
        f"  Error message: {result.error_message or 'No error message captured — test steps completed but assertion failed'}\n"
        f"  Screenshot captured: {'Yes — ' + result.screenshot_path if result.screenshot_path else 'No screenshot available'}\n"
        "\n"
        "SEVERITY DEFINITIONS (choose exactly one):\n"
        "  Critical - The application crashes, data is corrupted or lost, or a core user-facing feature is completely non-functional (e.g. cannot add contacts at all, delete destroys wrong data, form accepts clearly invalid input and corrupts state).\n"
        "  Major    - A feature does not work correctly but the app does not crash (e.g. search returns wrong results, edit saves to wrong record, UI count never updates).\n"
        "  Minor    - A cosmetic issue, a missing polish detail, or a partial degradation that does not block the user's core task (e.g. a label is wrong, a counter badge is stale, styling is broken).\n"
        "\n"
        "Your task: Respond ONLY with a valid JSON object. No explanation, no markdown, no code fences. Just raw JSON.\n"
        "\n"
        "Required JSON schema:\n"
        "{\n"
        "  \"severity\": \"Critical\" | \"Major\" | \"Minor\",\n"
        "  \"title\": \"Short bug title (max 10 words, like a Jira ticket title)\",\n"
        "  \"root_cause_hypothesis\": \"One sentence explaining the likely root cause in plain English\",\n"
        "  \"steps_to_reproduce\": [\"Step 1\", \"Step 2\", \"Step 3\"]\n"
        "}\n"
        "\n"
        "Rules for steps_to_reproduce:\n"
        "- Write them as a human tester would follow them manually\n"
        "- Be specific - reference actual UI labels, button names, field names\n"
        "- Include 2-5 steps maximum\n"
        "- The last step should describe the observed broken behaviour"
    )


def _normalize_severity(raw_severity: str) -> str:
    severity = raw_severity.strip()
    if severity in {"Critical", "Major", "Minor"}:
        return severity

    lowered = severity.lower()
    if lowered in {"critical", "high", "p1", "blocker"}:
        return "Critical"
    if lowered in {"major", "medium", "p2", "moderate"}:
        return "Major"
    if lowered in {"minor", "low", "p3", "trivial", "cosmetic"}:
        return "Minor"
    return "Major"


def _normalize_steps(raw_steps) -> list[str]:
    if isinstance(raw_steps, list):
        steps = [str(step).strip() for step in raw_steps if str(step).strip()]
        return steps

    if isinstance(raw_steps, str):
        steps = [line.strip() for line in raw_steps.splitlines() if line.strip()]
        return steps

    return []


def _fallback_bug(test_case: TestCase, result: TestResult) -> ClassifiedBug:
    return ClassifiedBug(
        test_id=test_case.id,
        severity=SeverityEnum.Major,
        title=f"Test failure: {test_case.title[:60]}",
        root_cause_hypothesis=(
            f"Automated classification failed. Raw error: {result.error_message}"
        ),
        steps_to_reproduce=test_case.steps,
        screenshot_path=result.screenshot_path,
        error_message=result.error_message,
    )


async def classify_bug(test_case: TestCase, result: TestResult) -> ClassifiedBug:
    settings = get_settings()
    prompt = _build_prompt(test_case, result)

    genai.configure(api_key=settings.gemini_api_key)
    model = genai.GenerativeModel(settings.gemini_model)

    failure_stage = "unknown"
    try:
        failure_stage = "gemini_api_call"
        response_text = await call_gemini_with_retry(model, prompt)

        failure_stage = "response_text_extraction"
        if not response_text.strip():
            raise ValueError("Gemini returned an empty response text for bug classification")

        failure_stage = "json_parsing"
        data = parse_gemini_json(response_text, expect_array=False)
        if not isinstance(data, dict):
            raise ValueError("Gemini response JSON for bug classification must be an object")
        parsed = data

        failure_stage = "normalization"
        normalized_severity = _normalize_severity(str(parsed.get("severity", "")))

        title = str(parsed.get("title", "")).strip()[:100]
        if not title:
            title = f"Test failure: {test_case.title[:60]}"

        root_cause_hypothesis = str(parsed.get("root_cause_hypothesis", "")).strip()
        if not root_cause_hypothesis:
            root_cause_hypothesis = (
                f"Test '{test_case.title}' failed with error: {result.error_message}"
            )

        steps_to_reproduce = _normalize_steps(parsed.get("steps_to_reproduce"))
        if not steps_to_reproduce:
            steps_to_reproduce = test_case.steps

        return ClassifiedBug(
            test_id=test_case.id,
            severity=SeverityEnum(normalized_severity),
            title=title,
            root_cause_hypothesis=root_cause_hypothesis,
            steps_to_reproduce=steps_to_reproduce,
            screenshot_path=result.screenshot_path,
            error_message=result.error_message,
        )
    except Exception as exc:  # pragma: no cover - must never halt pipeline
        logger.exception(
            "Bug classification fallback used for test %s at stage=%s, error=%s",
            test_case.id,
            failure_stage,
            exc,
        )
        return _fallback_bug(test_case, result)
