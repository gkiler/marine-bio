"""
Academic scraper - higheredjobs.com (higher education jobs)

BLOCKED: HigherEdJobs uses JavaScript-based bot detection (Cloudflare/PerimeterX)
that blocks all automated HTTP requests, including those with browser headers and cookies.
The site returns "Pardon Our Interruption" page for all requests.

This scraper is disabled and will return 0 jobs until a JavaScript-enabled solution
(Playwright, Selenium) is implemented.

Verified blocking on 2026-02-05:
- Search URLs: advanced_action.cfm blocked
- RSS feeds: jobFeed.cfm blocked
- All endpoints return bot detection page

Alternative: Manual job alerts or contact site for API access.
"""

import logging

from core.exceptions import ScraperError
from core.schemas import Job
from scrapers.base_scraper import BaseScraper
from scrapers.scraper_manager import register_scraper

logger = logging.getLogger(__name__)


@register_scraper
class Academic(BaseScraper):
    """
    Scraper for HigherEdJobs academic job board.

    Currently disabled due to JavaScript-based bot detection.
    """

    scraper_id = "academic"

    def search(self, query_params: dict | None = None) -> str:
        """
        HigherEdJobs blocks automated requests with bot detection.

        Raises ScraperError to indicate the site is not scrapable without JS.
        """
        logger.warning(
            "HigherEdJobs scraper is disabled: site uses bot detection that blocks "
            "all automated HTTP requests. Requires JavaScript-enabled browser (Playwright/Selenium)."
        )
        raise ScraperError(
            self.scraper_id,
            "Site blocked by bot detection - requires JavaScript execution",
            "https://www.higheredjobs.com/",
        )

    def parse(self, raw_data: str) -> list[Job]:
        """
        Not implemented - site requires JavaScript.

        This method will never be called since search() raises an error.
        """
        logger.error("Academic scraper parse() called - should not happen")
        return []
