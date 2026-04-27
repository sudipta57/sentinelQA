import logging

import google.generativeai as genai

from app.config import get_settings
from app.models import Sitemap, TestCase
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


def _build_prompt(sitemap: Sitemap, context: str, max_test_cases: int) -> str:
    lines: list[str] = [
        "You are an expert QA engineer. You have crawled a web application and discovered the following structure:",
        "",
        f"APP URL: {sitemap.base_url}",
    ]

    if context.strip():
        lines.append(f"CONTEXT: {context.strip()}")

    lines.extend(["", "DISCOVERED PAGES AND ELEMENTS:"])

    for page in sitemap.pages:
        lines.append(f"PAGE: {page.title} ({page.url})")
        lines.append("Interactive elements found:")
        for element in page.elements:
            lines.append(
                "  - "
                f"{element.tag} | "
                f"type={element.type} | "
                f"id={element.id} | "
                f"label=\"{element.label}\" | "
                f"placeholder=\"{element.placeholder}\""
            )

    lines.extend(
        [
            "",
            f"Your task: Generate between 8 and {max_test_cases} test cases that thoroughly test this application.",
            "",
            "You MUST include test cases of ALL these types:",
            "1. form_validation - test submitting forms with empty/invalid data",
            "2. navigation - test clicking links and navigating between pages",
            "3. ui_state - test that UI elements update correctly after user actions (counts, lists, etc.)",
            "4. error_handling - test edge cases like deleting items, submitting bad data",
            "5. edge_case - test unusual but valid interactions",
            "",
            "Rules:",
            "- Focus on flows a real user would do, not just checking if elements exist",
            "- Each test case must have concrete, executable steps (click X, type Y, check Z)",
            "- Steps must reference actual element labels, placeholders, or IDs found in the sitemap",
            "- expected_result must describe what SHOULD happen if the app works correctly",
            "- Do NOT generate duplicate or trivially similar test cases",
            "- Vary the target_element across different elements from the sitemap",
            "",
            "Respond ONLY with a valid JSON array. No explanation, no markdown, no code fences. Just the raw JSON array.",
            "",
            "Schema for each test case object:",
            "{",
            "  \"id\": \"tc_001\",",
            "  \"title\": \"...\",",
            "  \"type\": \"...\",",
            "  \"steps\": [\"...\", \"...\"],",
            "  \"expected_result\": \"...\",",
            "  \"target_element\": \"...\"",
            "}",
        ]
    )

    return "\n".join(lines)


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


def _is_quota_or_rate_limit_error(exc: Exception) -> bool:
    message = str(exc).lower()
    return "429" in message or "quota" in message or "rate limit" in message


def _candidate_models(settings) -> list[str]:
    candidates: list[str] = []

    primary = settings.gemini_model.strip()
    if primary:
        candidates.append(primary)

    fallback_raw = getattr(settings, "gemini_fallback_models", "") or ""
    for candidate in fallback_raw.split(","):
        cleaned = candidate.strip()
        if cleaned and cleaned not in candidates:
            candidates.append(cleaned)

    return candidates


async def generate_test_cases(sitemap: Sitemap, context: str = "") -> list[TestCase]:
    settings = get_settings()
    prompt = _build_prompt(sitemap, context, settings.max_test_cases)

    genai.configure(api_key=settings.gemini_api_key)

    response_text: str | None = None
    last_error: Exception | None = None
    models = _candidate_models(settings)

    for model_index, model_name in enumerate(models):
        model = genai.GenerativeModel(model_name)

        try:
            response_text = await call_gemini_with_retry(model, prompt)
            break
        except Exception as exc:  # pragma: no cover - network/provider variability
            last_error = exc
            if model_index < len(models) - 1 and _is_quota_or_rate_limit_error(exc):
                logger.warning(
                    "Gemini model %s exhausted quota; falling back to %s",
                    model_name,
                    models[model_index + 1],
                )
                continue
            if model_index == len(models) - 1:
                logger.warning("Gemini test generation failed on final model: %s", exc)

    if response_text is None:
        raise last_error if last_error else RuntimeError("Gemini did not return a response")

    data = parse_gemini_json(response_text, expect_array=True)
    if not isinstance(data, list):
        raise ValueError("Gemini response JSON must be an array of test cases")
    parsed_items = data

    limited_items = parsed_items[: settings.max_test_cases]
    test_cases = [_to_test_case(item) for item in limited_items]

    if len(test_cases) < 3:
        raise ValueError("Gemini generated too few test cases")

    return test_cases