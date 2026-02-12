"""
The Nature Conservancy careers scraper.

BLOCKED: TNC uses Phenom People career site with Angular-based job rendering.
The static HTML contains Angular templates (ng-* attributes) and placeholders,
but no actual job content.

This scraper is disabled and will return 0 jobs until a JavaScript-enabled solution
(Playwright, Selenium) is implemented.

Verified blocking on 2026-02-12:
- Site uses Phenom People ATS (careers.tnc.org)
- Angular templates with ng-* directives throughout
- Job elements have empty content (loaded client-side)
- Body text is only ~1500 chars of framework code
"""

import logging

from core.exceptions import ScraperError
from core.schemas import Job
from scrapers.base_scraper import BaseScraper
from scrapers.scraper_manager import register_scraper

logger = logging.getLogger(__name__)


@register_scraper
class TncScraper(BaseScraper):
    """
    Scraper for The Nature Conservancy job listings.

    Currently disabled due to Phenom People Angular rendering.
    """

    scraper_id = "tnc"

    def search(self, query_params: dict | None = None) -> str:
        """
        TNC uses Phenom People ATS that requires JavaScript execution.

        Raises ScraperError to indicate the site is not scrapable without JS.
        """
        logger.warning(
            "TNC scraper is disabled: site uses Phenom People ATS with Angular "
            "that renders all content client-side. Requires JavaScript-enabled browser (Playwright/Selenium)."
        )
        raise ScraperError(
            self.scraper_id,
            "Site requires JavaScript execution - Phenom People ATS with Angular",
            "https://careers.tnc.org/us/en/search-results",
        )

    def parse(self, raw_data: str) -> list[Job]:
        """
        Not implemented - site requires JavaScript.

        This method will never be called since search() raises an error.
        """
        return []
