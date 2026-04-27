import logging
import google.generativeai as genai

from app.config import get_settings
from app.models import ClassifiedBug, TestCase

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
            if any(x in error_str for x in ["429", "quota", "rate", "resource_exhausted", "500", "503"]):
                wait_seconds = (2 ** attempt) * 3
                logger.warning(f"Gemini retry {attempt+1}/{max_retries} in {wait_seconds}s: {e}")
                await _asyncio.sleep(wait_seconds)
                continue
            raise
    raise last_error


def _build_fix_prompt(bug: ClassifiedBug, test_case: TestCase) -> str:
    """Build the prompt for fix suggestion generation."""
    steps_text = "\n".join(f"    {i+1}. {step}" for i, step in enumerate(test_case.steps))
    
    return (
        "You are a senior software engineer reviewing a bug found by an automated QA agent. "
        "The agent tested a live web application WITHOUT access to the source code — it only "
        "observed browser behaviour.\n"
        "\n"
        "Based on the observed failure, generate a concrete fix suggestion for the developer who "
        "owns this code.\n"
        "\n"
        "BUG DETAILS:\n"
        f"  Severity: {bug.severity.value}\n"
        f"  Title: {bug.title}\n"
        f"  Root cause hypothesis: {bug.root_cause_hypothesis}\n"
        "\n"
        "WHAT WAS TESTED:\n"
        f"  Test title: {test_case.title}\n"
        f"  Test type: {test_case.type}\n"
        "  Steps executed:\n"
        f"{steps_text}\n"
        f"  Expected result: {test_case.expected_result}\n"
        "\n"
        "WHAT ACTUALLY HAPPENED:\n"
        f"  Error: {bug.error_message or 'Test steps completed but expected behaviour was not observed'}\n"
        "\n"
        "YOUR TASK:\n"
        "Write a fix suggestion for the developer. Follow these rules:\n"
        "1. Write in plain English — no jargon, no fluff\n"
        "2. Be specific about WHAT to change and WHERE (even without seeing the code, reason from "
        "the observed behaviour)\n"
        "3. Include a short code snippet or pseudocode example if it helps clarify the fix\n"
        "4. Keep it to 3-5 sentences maximum\n"
        "5. Start with the action verb — 'Add...', 'Fix...', 'Check...', 'Replace...'\n"
        "6. Do NOT say 'I think' or 'possibly' — be direct and confident\n"
        "\n"
        "Respond with ONLY the fix suggestion text. No title, no preamble, no markdown headers. "
        "Just the plain fix suggestion paragraph."
    )


def _generate_fallback_fix(bug: ClassifiedBug) -> str:
    """Generate a fallback fix suggestion when Gemini call fails."""
    severity = bug.severity.value
    if severity == "Critical":
        return (
            f"Fix the critical issue identified in '{bug.title}'. "
            f"Review the component handling this interaction and add proper validation, error handling, "
            f"or state management as appropriate. Root cause: {bug.root_cause_hypothesis}"
        )
    else:
        return (
            f"Address the issue in '{bug.title}'. Review the relevant component logic and ensure the "
            f"expected behaviour is correctly implemented. Root cause: {bug.root_cause_hypothesis}"
        )


async def suggest_fix(bug: ClassifiedBug, test_case: TestCase) -> str:
    """
    Generate a concrete fix suggestion for a classified bug using Gemini.
    
    Args:
        bug: The classified bug to suggest a fix for
        test_case: The test case that exposed the bug
    
    Returns:
        A plain-text fix suggestion for the developer
    """
    settings = get_settings()
    genai.configure(api_key=settings.gemini_api_key)
    model = genai.GenerativeModel(settings.gemini_model)

    prompt = _build_fix_prompt(bug, test_case)

    try:
        response_text = await call_gemini_with_retry(model, prompt)
        fix = response_text.strip()
        # Remove any accidental markdown
        fix = fix.strip("*#`").strip()
        if not fix:
            return _generate_fallback_fix(bug)
        return fix
    except Exception as e:
        logger.warning(f"suggest_fix failed for {bug.test_id}: {e}")
        return _generate_fallback_fix(bug)
