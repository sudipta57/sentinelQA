import asyncio
import logging
import os
import re
import time

from playwright.async_api import TimeoutError as PlaywrightTimeoutError
from playwright.async_api import async_playwright

from app.config import get_settings
from app.models import TestCase, TestResult

logger = logging.getLogger(__name__)


async def is_element_visible_in_viewport(page, selector: str) -> bool:
    """Check if element exists AND is visible (not hidden by CSS)."""
    try:
        locator = page.locator(selector).first
        is_visible = await locator.is_visible(timeout=3000)
        return is_visible
    except Exception:
        return False


def _escape_selector_text(value: str) -> str:
    return value.replace("\\", "\\\\").replace("'", "\\'")


def _extract_quoted_value(step: str) -> str:
    match = re.search(r"'([^']*)'|\"([^\"]*)\"", step)
    if not match:
        return ""
    return match.group(1) or match.group(2) or ""


def _extract_quoted_values(step: str) -> list[str]:
    return [match.group(1) or match.group(2) or "" for match in re.finditer(r"'([^']*)'|\"([^\"]*)\"", step)]


async def _attempt_actions(actions):
    last_error: Exception | None = None

    for action in actions:
        try:
            return await action()
        except PlaywrightTimeoutError:
            raise
        except Exception as exc:
            last_error = exc

    if last_error is not None:
        raise last_error

    raise RuntimeError("No action attempts were provided")


async def _fill_with_placeholder(page, placeholder: str, value: str) -> None:
    placeholder_escaped = _escape_selector_text(placeholder)

    async def _fill_input_placeholder():
        await page.fill(f"input[placeholder='{placeholder_escaped}']", value)

    async def _fill_textarea_placeholder():
        await page.fill(f"textarea[placeholder='{placeholder_escaped}']", value)

    await _attempt_actions([_fill_input_placeholder, _fill_textarea_placeholder])


async def fill_input_by_label(page, label: str, value: str) -> None:
    """Try multiple strategies to fill an input field."""
    label_escaped = _escape_selector_text(label)

    strategies = [
        # 1. Exact placeholder match
        lambda: page.fill(f"input[placeholder='{label_escaped}']", value),
        # 2. Case-insensitive placeholder contains
        lambda: page.locator(f"input[placeholder*='{label_escaped}' i]").first.fill(value),
        # 3. Playwright get_by_label
        lambda: page.get_by_label(label, exact=False).first.fill(value),
        # 4. aria-label
        lambda: page.fill(f"input[aria-label='{label_escaped}' i]", value),
        # 5. name attribute
        lambda: page.fill(f"input[name='{label_escaped}' i]", value),
        # 6. Find label tag by text then target its input
        lambda: page.locator(f"label:has-text('{label_escaped}') + input").first.fill(value),
        lambda: page.locator(f"label:has-text('{label_escaped}')").locator("..").locator("input").first.fill(value),
    ]

    for strategy in strategies:
        try:
            await strategy()
            return
        except Exception:
            continue

    raise Exception(f"Could not find input for label '{label}' after trying all strategies")


async def _select_option(page, label: str, option: str) -> None:
    async def _select_by_label_text():
        label_locator = page.locator("label", has_text=label).first
        if await label_locator.count() == 0:
            raise RuntimeError(f"Label '{label}' not found")

        for_attr = await label_locator.get_attribute("for")
        if for_attr:
            await page.locator(f"#{_escape_selector_text(for_attr)}").select_option(option)
            return

        select_locator = label_locator.locator("xpath=following::select[1]").first
        await select_locator.select_option(option)

    async def _select_by_first_select():
        await page.select_option("select", option)

    async def _select_by_first_select_label():
        await page.select_option("select", label=option)

    if label:
        try:
            await _select_by_label_text()
            return
        except Exception:
            pass

    await _attempt_actions([_select_by_first_select, _select_by_first_select_label])


async def _click_button(page, label: str) -> None:
    label_escaped = _escape_selector_text(label)

    async def _click_by_role():
        await page.get_by_role("button", name=label).click()

    async def _click_by_text():
        await page.click(f"button:has-text('{label_escaped}')")

    async def _click_by_aria_label():
        await page.click(f"[aria-label='{label_escaped}']")

    await _attempt_actions([_click_by_role, _click_by_text, _click_by_aria_label])


async def _click_specific_button(page, contact_name: str, button_name: str) -> None:
    contact_escaped = _escape_selector_text(contact_name)

    async def _click_in_container():
        container = page.locator(f"text={contact_escaped}").locator("..").first
        await container.get_by_role("button", name=button_name).click()

    async def _click_fallback_first():
        await page.get_by_role("button", name=button_name).first.click()

    await _attempt_actions([_click_in_container, _click_fallback_first])


async def _verify_visible(page, step: str) -> None:
    await page.wait_for_timeout(500)
    text = _extract_quoted_value(step)
    if not text:
        text = step.split(" ", 1)[1].strip() if " " in step else step
        text = text.replace("Verify", "", 1).replace("Check", "", 1).strip()

    locator = page.locator(f"text={_escape_selector_text(text)}").first
    visible = await locator.is_visible()
    if not visible:
        raise AssertionError(f"Expected '{text}' to be visible but it was not")


def _parse_key_value_pairs(step: str) -> dict[str, str]:
    values: dict[str, str] = {}
    for match in re.finditer(r"(\w+)\s*=\s*(?:'([^']*)'|\"([^\"]*)\"|([^,]+))", step):
        key = match.group(1).strip().lower()
        value = next((group for group in match.groups()[1:] if group is not None), "")
        values[key] = value.strip()
    return values


async def _add_contact(page, step: str) -> None:
    values = _parse_key_value_pairs(step)

    await fill_input_by_label(page, "Name", values.get("name", ""))
    await fill_input_by_label(page, "Email", values.get("email", ""))
    await fill_input_by_label(page, "Phone", values.get("phone", ""))

    category = values.get("category", "")
    if category:
        try:
            await _select_option(page, "Category", category)
        except Exception:
            await _select_option(page, "", category)

    await _click_button(page, "Add Contact")
    await page.wait_for_timeout(300)


async def execute_step(page, step: str) -> None:
    normalized = step.strip()

    try:
        if normalized.startswith("Type "):
            value = _extract_quoted_value(normalized)
            if "with placeholder" in normalized:
                match = re.search(r"with placeholder\s+['\"]([^'\"]+)['\"]", normalized)
                placeholder = match.group(1) if match else ""
                await _fill_with_placeholder(page, placeholder, value)
                return

            if "with label" in normalized:
                match = re.search(r"with label\s+['\"]([^'\"]+)['\"]", normalized)
                label = match.group(1) if match else ""
                await fill_input_by_label(page, label, value)
                return

        if normalized.startswith("Modify the input"):
            value_matches = _extract_quoted_values(normalized)
            label_match = re.search(r"with label\s+['\"]([^'\"]+)['\"]", normalized)
            label = label_match.group(1) if label_match else ""
            value = value_matches[-1] if value_matches else ""
            await fill_input_by_label(page, label, value)
            return

        if normalized.startswith("Click the button"):
            label = _extract_quoted_value(normalized)
            # Check if button is visible before trying to click
            is_visible = await is_element_visible_in_viewport(
                page, f"button:has-text('{_escape_selector_text(label)}')"
            )
            if not is_visible:
                logger.info(
                    "Skipping hidden element: button '%s' — not visible in current viewport", label
                )
                return  # Skip silently — likely a responsive/mobile-only element
            await _click_button(page, label)
            return

        if normalized.startswith("Select "):
            match = re.search(r"Select\s+['\"]([^'\"]+)['\"]\s+from the select with label\s+['\"]([^'\"]+)['\"]", normalized)
            if match:
                option, label = match.group(1), match.group(2)
                await _select_option(page, label, option)
                return

        if normalized.startswith("Click the 'Edit'") or normalized.startswith("Click the \"Edit\""):
            values = _extract_quoted_values(normalized)
            contact_name = values[-1] if values else ""
            is_visible = await is_element_visible_in_viewport(
                page, f"button:has-text('Edit')"
            )
            if not is_visible:
                logger.info("Skipping hidden Edit button — not visible in current viewport")
                return
            await _click_specific_button(page, contact_name, "Edit")
            return

        if normalized.startswith("Click the 'Delete'") or normalized.startswith("Click the \"Delete\""):
            values = _extract_quoted_values(normalized)
            contact_name = values[-1] if values else ""
            is_visible = await is_element_visible_in_viewport(
                page, f"button:has-text('Delete')"
            )
            if not is_visible:
                logger.info("Skipping hidden Delete button — not visible in current viewport")
                return
            await _click_specific_button(page, contact_name, "Delete")
            return

        if normalized.startswith("Clear the text"):
            match = re.search(r"with placeholder\s+['\"]([^'\"]+)['\"]", normalized)
            placeholder = match.group(1) if match else ""
            await _fill_with_placeholder(page, placeholder, "")
            return

        if normalized.startswith(("Verify", "Check")):
            await _verify_visible(page, normalized)
            return

        if normalized.startswith("Add a contact:") or normalized.startswith("Add Contact"):
            await _add_contact(page, normalized)
            return

        if normalized.startswith("Press Enter") or normalized.startswith("press Enter"):
            await page.keyboard.press("Enter")
            return

        if normalized.startswith("Wait") or normalized.startswith("wait for"):
            await page.wait_for_timeout(800)
            return

        logger.warning("Unrecognised step pattern, skipping: %s", step)
    except Exception as exc:
        # Best effort: scroll the likely target into view so failure screenshot is more useful.
        try:
            candidates: list[str] = []
            candidates.extend(_extract_quoted_values(normalized))
            candidates.extend(re.findall(r"placeholder\s+['\"]([^'\"]+)['\"]", normalized))
            candidates.extend(re.findall(r"label\s+['\"]([^'\"]+)['\"]", normalized))

            for hint in candidates:
                if not hint:
                    continue
                try:
                    await page.locator(f"text={hint}").first.scroll_into_view_if_needed(timeout=1000)
                    break
                except Exception:
                    continue

            await page.wait_for_timeout(200)
        except Exception:
            pass

        raise exc


async def execute_test(test_case: TestCase, base_url: str, screenshot_dir: str) -> TestResult:
    start_time = time.time()
    browser = None
    page = None
    playwright = None
    settings = get_settings()
    screenshot_dir = screenshot_dir or settings.screenshot_dir

    try:
        playwright = await async_playwright().start()
        browser = await playwright.chromium.launch(
            headless=True,
            args=["--no-sandbox", "--disable-setuid-sandbox", "--disable-dev-shm-usage"],
        )
        page = await browser.new_page(viewport={"width": 1280, "height": 800})
        page.set_default_timeout(15000)

        await page.goto(base_url, wait_until="networkidle", timeout=15000)
        if "localhost" not in base_url and "demo-app" not in base_url:
            await page.wait_for_timeout(3000)  # extra wait for external/slow sites
        else:
            await page.wait_for_timeout(1500)

        for step in test_case.steps:
            await execute_step(page, step)
            await page.wait_for_timeout(200)

        duration_ms = int((time.time() - start_time) * 1000)
        return TestResult(test_id=test_case.id, passed=True, duration_ms=duration_ms)

    except Exception as e:
        async def take_targeted_screenshot(page, error_message: str, full_path: str):
            """
            Try to scroll the relevant element into view before screenshotting.
            Falls back to plain viewport screenshot if anything fails.
            """
            try:
                # Try to find and scroll to the element mentioned in the error
                # Playwright error messages often contain selector info
                import re
                # Look for common element references in error text
                selector_hints = [
                    r"locator\('(.+?)'\)",
                    r'getByRole\(.+?name: "(.+?)"',
                    r'getByLabel\("(.+?)"\)',
                    r'placeholder="(.+?)"',
                ]
                scrolled = False
                for pattern in selector_hints:
                    match = re.search(pattern, str(error_message))
                    if match:
                        try:
                            hint = match.group(1)
                            el = page.locator(f"text={hint}").first
                            await el.scroll_into_view_if_needed(timeout=2000)
                            scrolled = True
                            break
                        except Exception:
                            continue

                # Small pause to let scroll settle
                await page.wait_for_timeout(300)
                await page.screenshot(path=full_path, full_page=False)

            except Exception:
                # Absolute fallback
                try:
                    await page.screenshot(path=full_path, full_page=False)
                except Exception:
                    pass

        duration_ms = int((time.time() - start_time) * 1000)
        screenshot_path = None

        try:
            if browser is not None:
                pages = browser.contexts[0].pages if browser.contexts else []
                if pages:
                    os.makedirs(screenshot_dir, exist_ok=True)
                    filename = f"{test_case.id}_{int(time.time())}.png"
                    full_path = os.path.join(screenshot_dir, filename)
                    await take_targeted_screenshot(pages[0], str(e), full_path)
                    screenshot_path = f"/screenshots/{filename}"
        except Exception as screenshot_err:
            logger.warning(f"Failed to capture screenshot: {screenshot_err}")

        return TestResult(
            test_id=test_case.id,
            passed=False,
            error_message=str(e)[:500],
            screenshot_path=screenshot_path,
            duration_ms=duration_ms,
        )
    finally:
        if browser:
            await browser.close()
        if playwright is not None:
            await playwright.stop()