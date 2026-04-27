import json
import re
import logging

logger = logging.getLogger(__name__)


def parse_gemini_json(text: str, expect_array: bool = False):
    """
    Robustly parse JSON from a Gemini response.
    Handles markdown fences, leading/trailing text, extra whitespace.
    Returns [] if expect_array=True on failure, {} otherwise.
    """
    fallback = [] if expect_array else {}
    if not text or not text.strip():
        logger.warning("parse_gemini_json received empty text")
        return fallback

    cleaned = text.strip()

    # Remove markdown code fences (```json ... ``` or ``` ... ```)
    cleaned = re.sub(r"^```(?:json)?\s*\n?", "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\n?```\s*$", "", cleaned)
    cleaned = cleaned.strip()

    # Direct parse attempt
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        pass

    # Try extracting array [...] — for generate_test_cases and reflect_and_expand
    if expect_array:
        match = re.search(r"\[.*\]", cleaned, re.DOTALL)
        if match:
            try:
                return json.loads(match.group())
            except json.JSONDecodeError:
                pass

    # Try extracting object {...} — for classify_bug and generate_report summary
    match = re.search(r"\{.*\}", cleaned, re.DOTALL)
    if match:
        try:
            return json.loads(match.group())
        except json.JSONDecodeError:
            pass

    logger.warning(f"parse_gemini_json: all parse attempts failed. Input preview: {text[:300]}")
    return fallback
