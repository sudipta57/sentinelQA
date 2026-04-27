import logging

import google.generativeai as genai

from app.config import get_settings
from app.models import ClassifiedBug, Sitemap, TestCase
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

_VALID_TEST_TYPES = {
    "form_validation",
    "navigation",
    "ui_state",
    "error_handling",
    "edge_case",
}


def _page_elements_summary(page) -> str:
    elements = [e.label or e.type for e in page.elements[:10] if e.label or e.type]
    return ", ".join(elements)


def _build_prompt(bugs: list[ClassifiedBug], tested_flows: list[str], sitemap: Sitemap) -> str:
    tested_lines = "\n".join(f"  - {flow}" for flow in tested_flows)
    bug_lines = "\n".join(
        f"  - [{b.severity.value}] {b.title}: {b.root_cause_hypothesis}" for b in bugs
    )
    element_lines = "\n".join(
        f"  PAGE: {p.title} | Elements: {_page_elements_summary(p)}" for p in sitemap.pages
    )

    return f"""You are a senior QA engineer reviewing the results of an automated test run. Your job is to identify coverage gaps and suggest additional targeted test cases.

APPLICATION: {sitemap.base_url}

WHAT WAS ALREADY TESTED ({len(tested_flows)} flows):
{tested_lines}

BUGS FOUND SO FAR ({len(bugs)} bugs):
{bug_lines}

AVAILABLE ELEMENTS IN THE APP:
{element_lines}

Your task: Review what has been tested. Identify any important user flows that were NOT covered.

If you find meaningful coverage gaps, return up to 5 new targeted test cases focusing on:
- Flows directly related to the bugs found (e.g. if delete is broken, test delete of the last item)
- Edge cases that were not tested yet
- Interactions between features (e.g. search after adding a contact)

If coverage is already sufficient (all major flows tested), return an empty array [].

IMPORTANT: Only return new test cases that are meaningfully different from what was already tested.
Do not return tests just to fill a quota — an empty array is the correct answer if coverage is sufficient.

Respond ONLY with a valid JSON array (may be empty []). No explanation, no markdown, no code fences.

Same TestCase schema as before:
{{
  "id": "tc_reflect_001",
  "title": "...",
  "type": "form_validation" | "navigation" | "ui_state" | "error_handling" | "edge_case",
  "steps": ["..."],
  "expected_result": "...",
  "target_element": "..."
}}

Use IDs starting from tc_reflect_001, tc_reflect_002, etc."""


def _to_test_case(raw_item: dict) -> TestCase:
    if not isinstance(raw_item, dict):
        raise ValueError("Each generated test case must be a JSON object")

    required = ["id", "title", "type", "steps", "expected_result"]
    missing = [key for key in required if key not in raw_item]
    if missing:
        raise ValueError(f"Generated test case missing required fields: {', '.join(missing)}")

    raw_type = str(raw_item.get("type", "")).strip()
    normalized_type = raw_type if raw_type in _VALID_TEST_TYPES else "edge_case"

    raw_steps = raw_item.get("steps")
    if not isinstance(raw_steps, list):
        raise ValueError("Generated test case 'steps' must be a list")

    item = {
        "id": str(raw_item.get("id", "")).strip(),
        "title": str(raw_item.get("title", "")).strip(),
        "type": normalized_type,
        "steps": [str(step).strip() for step in raw_steps if str(step).strip()],
        "expected_result": str(raw_item.get("expected_result", "")).strip(),
        "target_element": (
            str(raw_item.get("target_element")).strip()
            if raw_item.get("target_element") is not None
            else None
        ),
    }

    return TestCase(**item)


async def reflect_and_expand(
    bugs: list[ClassifiedBug],
    tested_flows: list[str],
    sitemap: Sitemap,
) -> list[TestCase]:
    settings = get_settings()

    try:
        genai.configure(api_key=settings.gemini_api_key)
        model = genai.GenerativeModel(settings.gemini_model)
        prompt = _build_prompt(bugs, tested_flows, sitemap)

        response_text = await call_gemini_with_retry(model, prompt)
        if not response_text.strip():
            return []

        data = parse_gemini_json(response_text, expect_array=True)
        if not isinstance(data, list):
            logger.warning("Reflection JSON parsing failed: response was not an array")
            return []
        parsed_items = data

        if not parsed_items:
            return []

        test_cases: list[TestCase] = []
        for item in parsed_items[:5]:
            try:
                test_cases.append(_to_test_case(item))
            except Exception as exc:
                logger.warning("Skipping invalid reflected test case: %s", exc)

        return test_cases
    except Exception as exc:  # pragma: no cover - reflection must never halt pipeline
        logger.warning("Reflection step failed; returning no follow-up cases: %s", exc)
        return []