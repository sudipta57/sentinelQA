import logging

import google.generativeai as genai

from app.config import get_settings
from app.models import BugsBySeverity, ClassifiedBug, Report, SeverityEnum, TestResult
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


def _build_prompt(
    all_results: list[TestResult],
    all_bugs: list[ClassifiedBug],
    app_url: str,
) -> str:
    passed = sum(1 for r in all_results if r.passed)
    failed = len(all_results) - passed
    critical_count = sum(1 for b in all_bugs if b.severity == SeverityEnum.Critical)
    major_count = sum(1 for b in all_bugs if b.severity == SeverityEnum.Major)
    minor_count = sum(1 for b in all_bugs if b.severity == SeverityEnum.Minor)
    bug_lines = "\n".join(f"  - [{b.severity.value}] {b.title}" for b in all_bugs)

    return f"""You are writing a brief executive summary for an automated QA report.

Application tested: {app_url}
Total tests run: {len(all_results)}
Passed: {passed}  Failed: {failed}
Bugs found: {len(all_bugs)} ({critical_count} Critical, {major_count} Major, {minor_count} Minor)

Bug titles:
{bug_lines}

Write:
1. "summary": One sentence (max 30 words) describing the overall health of this application for a non-technical reader.
2. "recommendations": A list of exactly 3 short, actionable recommendations for the developer (each max 20 words).

Respond ONLY with valid JSON. No markdown, no code fences.
Schema:
{{
  "summary": "...",
  "recommendations": ["...", "...", "..."]
}}"""


async def generate_report(
    all_results: list[TestResult],
    all_bugs: list[ClassifiedBug],
    app_url: str,
    run_duration_ms: int,
) -> Report:
    settings = get_settings()
    passed = sum(1 for r in all_results if r.passed)
    failed = len(all_results) - passed

    # Filter out false positives — they must never appear in the final report
    real_bugs = [b for b in all_bugs if b.severity != SeverityEnum.false_positive]

    critical_bugs = [b for b in real_bugs if b.severity == SeverityEnum.Critical]
    major_bugs = [b for b in real_bugs if b.severity == SeverityEnum.Major]
    minor_bugs = [b for b in real_bugs if b.severity == SeverityEnum.Minor]

    summary = f"Automated scan of {app_url} found {len(real_bugs)} bug(s) across {len(all_results)} test cases."
    recommendations = [
        "Fix all Critical severity bugs before next release.",
        "Add input validation to all form fields.",
        "Implement automated regression tests to prevent future regressions.",
    ]

    try:
        genai.configure(api_key=settings.gemini_api_key)
        model = genai.GenerativeModel(settings.gemini_model)
        prompt = _build_prompt(all_results, real_bugs, app_url)
        response_text = await call_gemini_with_retry(model, prompt)

        if response_text.strip():
            data = parse_gemini_json(response_text, expect_array=False)
            if not isinstance(data, dict):
                raise ValueError("Gemini response JSON for report generation must be an object")
            parsed = data
            parsed_summary = str(parsed.get("summary", "")).strip()
            parsed_recommendations = parsed.get("recommendations", [])

            if parsed_summary:
                summary = parsed_summary

            if isinstance(parsed_recommendations, list):
                normalized_recommendations = [
                    str(item).strip() for item in parsed_recommendations if str(item).strip()
                ]
                if len(normalized_recommendations) == 3:
                    recommendations = normalized_recommendations
    except Exception as exc:  # pragma: no cover - must never halt pipeline
        logger.warning("Report summary generation failed; using fallback content: %s", exc)

    return Report(
        app_url=app_url,
        summary=summary,
        total_tests=len(all_results),
        passed=passed,
        failed=failed,
        bugs_by_severity=BugsBySeverity(
            critical=critical_bugs,
            major=major_bugs,
            minor=minor_bugs,
        ),
        recommendations=recommendations,
        run_duration_ms=run_duration_ms,
    )