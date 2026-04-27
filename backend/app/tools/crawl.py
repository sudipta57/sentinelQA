import asyncio
import logging
from urllib.parse import urljoin, urlparse

from playwright.async_api import ElementHandle, Page, async_playwright

from app.models import PageElement, PageInfo, Sitemap

logger = logging.getLogger(__name__)

_INTERACTIVE_SELECTOR = "input, button, a[href], select, textarea, form, [role='button'], [onclick]"


async def _safe_inner_text(element: ElementHandle) -> str | None:
    try:
        text = await element.inner_text()
    except Exception:
        return None

    text = text.strip()
    if not text:
        return None
    return text[:50]


async def extract_elements(page: Page) -> list[PageElement]:
    elements: list[PageElement] = []

    try:
        handles = await page.query_selector_all(_INTERACTIVE_SELECTOR)
    except Exception:
        return elements

    for el in handles:
        try:
            tag_prop = await el.get_property("tagName")
            raw_tag = await tag_prop.json_value()
            tag_name = (str(raw_tag).lower() if raw_tag else "")

            element_type = await el.get_attribute("type")
            element_id = await el.get_attribute("id")
            name = await el.get_attribute("name")
            placeholder = await el.get_attribute("placeholder")
            href = await el.get_attribute("href") if tag_name == "a" else None

            label = await _safe_inner_text(el)
            if not label:
                aria_label = await el.get_attribute("aria-label")
                if aria_label:
                    label = aria_label.strip()[:50] or None
            if not label and placeholder:
                label = placeholder.strip()[:50] or None

            if (not label or not label.strip()) and not placeholder and not href:
                continue

            elements.append(
                PageElement(
                    type=element_type or tag_name or "unknown",
                    id=element_id,
                    label=label,
                    placeholder=placeholder,
                    href=href,
                    tag=tag_name or "unknown",
                )
            )
        except Exception:
            # Skip elements that fail extraction to keep crawl resilient.
            continue

    return elements


async def _collect_page_info(page: Page) -> PageInfo:
    page_title = await page.title()
    elements = await extract_elements(page)
    return PageInfo(url=page.url, title=page_title, elements=elements)


def _is_same_origin(candidate: str, base) -> bool:
    parsed = urlparse(candidate)
    return parsed.scheme == base.scheme and parsed.hostname == base.hostname


async def crawl_app(url: str, max_pages: int = 5) -> Sitemap:
    max_pages = max(1, max_pages)
    all_pages: list[PageInfo] = []
    visited: set[str] = set()

    base_url = urlparse(url)
    if not base_url.scheme or not base_url.netloc:
        raise ValueError(f"Could not reach {url}: invalid URL")

    async with async_playwright() as playwright:
        browser = None
        try:
            browser = await playwright.chromium.launch(
                headless=True,
                args=["--no-sandbox", "--disable-setuid-sandbox", "--disable-dev-shm-usage"],
            )
            page = await browser.new_page()

            try:
                await page.goto(url, wait_until="networkidle", timeout=30000)
                await page.wait_for_timeout(2000)
            except Exception as e:
                raise ValueError(f"Could not reach {url}: {e}") from e

            all_pages.append(await _collect_page_info(page))
            visited.add(page.url.split("#", 1)[0])

            if len(all_pages) >= max_pages:
                return Sitemap(pages=all_pages, base_url=str(base_url))

            try:
                link_handles = await page.query_selector_all("a[href]")
            except Exception:
                link_handles = []

            candidate_links: list[str] = []
            for link in link_handles:
                try:
                    href = await link.get_attribute("href")
                    if not href:
                        continue

                    raw_href = href.strip()
                    lowered = raw_href.lower()
                    if not raw_href or lowered.startswith("#"):
                        continue
                    if lowered.startswith("javascript:") or lowered.startswith("mailto:"):
                        continue

                    absolute = urljoin(page.url, raw_href)
                    absolute_no_fragment = absolute.split("#", 1)[0]

                    if not _is_same_origin(absolute_no_fragment, base_url):
                        continue
                    if absolute_no_fragment in visited:
                        continue

                    visited.add(absolute_no_fragment)
                    candidate_links.append(absolute_no_fragment)
                except Exception:
                    continue

            for target in candidate_links:
                if len(all_pages) >= max_pages:
                    break

                try:
                    await page.goto(target, wait_until="networkidle", timeout=30000)
                    await page.wait_for_timeout(2000)
                    all_pages.append(await _collect_page_info(page))
                except Exception as e:
                    logger.warning("Skipping sub-page %s due to navigation error: %s", target, e)
                    continue

            return Sitemap(pages=all_pages, base_url=str(base_url))
        finally:
            if browser is not None:
                await browser.close()
