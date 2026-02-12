"""
Base scraper for sites that require JavaScript rendering.

Extends BaseScraper with a fetch_rendered() method that uses Playwright's
sync API to load pages in a headless Chromium browser. JS-requiring scrapers
inherit from this instead of BaseScraper.

Thread safety: Playwright instances must not be shared across threads. Each
PlaywrightScraper instance lazily creates its own Playwright + browser, so
the ThreadPoolExecutor in scraper_manager (max_workers=5) gets at most 5
browser processes — fine for a dev machine.
"""

import logging

from config.settings import settings
from scrapers.base_scraper import BaseScraper

logger = logging.getLogger(__name__)


class PlaywrightScraper(BaseScraper):
    """
    Base for scrapers that need JavaScript rendering.

    Adds fetch_rendered() on top of BaseScraper's caching, rate limiting,
    and retry infrastructure. The httpx client is still available for any
    plain HTTP requests a subclass might need.
    """

    def __init__(self) -> None:
        super().__init__()
        self._playwright = None
        self._browser = None

    def _ensure_browser(self) -> None:
        """Lazy-start Playwright + Chromium (one per scraper instance)."""
        if self._browser is None:
            from playwright.sync_api import sync_playwright

            self._playwright = sync_playwright().start()
            self._browser = self._playwright.chromium.launch(headless=True)

    def fetch_rendered(
        self,
        url: str,
        wait_selector: str | None = None,
        timeout: int | None = None,
    ) -> str:
        """
        Navigate to URL, wait for JS to render, return full page HTML.

        Args:
            url: Page to load.
            wait_selector: CSS selector to wait for before capturing HTML.
                If None, waits for networkidle only.
            timeout: Page load timeout in ms. Defaults to settings.playwright_timeout.

        Returns:
            Rendered HTML string.
        """
        self._ensure_browser()
        self.limiter.acquire_sync()

        timeout = timeout or settings.playwright_timeout
        page = self._browser.new_page()
        try:
            page.goto(url, timeout=timeout, wait_until="networkidle")
            if wait_selector:
                page.wait_for_selector(wait_selector, timeout=timeout)
            html = page.content()
            logger.debug(
                "%s: rendered %s (%d chars)", self.scraper_id, url, len(html)
            )
            return html
        finally:
            page.close()

    def close(self) -> None:
        """Clean up browser + Playwright, then httpx client."""
        if self._browser:
            self._browser.close()
            self._browser = None
        if self._playwright:
            self._playwright.stop()
            self._playwright = None
        super().close()
