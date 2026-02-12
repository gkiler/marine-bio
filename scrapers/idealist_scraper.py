"""
Idealist scraper - idealist.org (filtered by environment/science)

BLOCKED: Idealist is a React single-page application (SPA) that renders all job
listings dynamically via JavaScript. The static HTML contains only an empty #root div
with no body content at all.

This scraper is disabled and will return 0 jobs until a JavaScript-enabled solution
(Playwright, Selenium) is implemented.

Verified blocking on 2026-02-12:
- Site uses React SPA with client-side rendering
- Body is completely empty (0 chars)
- No job listings present in static HTML
"""

import logging

from core.exceptions import ScraperError
from core.schemas import Job
from scrapers.base_scraper import BaseScraper
from scrapers.scraper_manager import register_scraper

logger = logging.getLogger(__name__)


@register_scraper
class Idealist(BaseScraper):
    """
    Scraper for Idealist nonprofit/social impact job board.

    Currently disabled due to JavaScript-based SPA rendering.
    """

    scraper_id = "idealist"

    def search(self, query_params: dict | None = None) -> str:
        """
        Idealist uses React SPA that requires JavaScript execution.

        Raises ScraperError to indicate the site is not scrapable without JS.
        """
        logger.warning(
            "Idealist scraper is disabled: site uses React SPA that renders "
            "all content client-side. Requires JavaScript-enabled browser (Playwright/Selenium)."
        )
        raise ScraperError(
            self.scraper_id,
            "Site requires JavaScript execution - React SPA with client-side rendering",
            "https://www.idealist.org/en/jobs",
        )

    def parse(self, raw_data: str) -> list[Job]:
        """
        Not implemented - site requires JavaScript.

        This method will never be called since search() raises an error.
        """
        return []
