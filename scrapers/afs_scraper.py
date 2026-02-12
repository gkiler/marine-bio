"""
American Fisheries Society job scraper.

BLOCKED: jobs.fisheries.org uses Cloudflare JavaScript challenge
that blocks all automated HTTP requests, including those with full browser headers.
The site returns 403 Forbidden with a "Just a moment..." challenge page.

This scraper is disabled and will return 0 jobs until a JavaScript-enabled solution
(Playwright, Selenium) is implemented.

Verified blocking on 2026-02-12:
- Main job board: jobs.fisheries.org blocked (cf-mitigated: challenge)
- Alternative paths: /careers/, /employment/, /jobs/ all blocked
- Entire fisheries.org domain protected by Cloudflare
- Response header: 'cf-mitigated': 'challenge'

Alternative: Manual job alerts or contact AFS for API access.
"""

import logging

from core.exceptions import ScraperError
from core.schemas import Job
from scrapers.base_scraper import BaseScraper
from scrapers.scraper_manager import register_scraper

logger = logging.getLogger(__name__)


@register_scraper
class AFSScraper(BaseScraper):
    """
    Scraper for American Fisheries Society job board.

    Currently disabled due to Cloudflare JavaScript challenge.
    """

    scraper_id = "afs"

    def search(self, query_params: dict | None = None) -> str:
        """
        AFS job board blocks automated requests with Cloudflare challenge.

        Raises ScraperError to indicate the site is not scrapable without JS.
        """
        logger.warning(
            "AFS scraper is disabled: jobs.fisheries.org uses Cloudflare JavaScript "
            "challenge that blocks all automated HTTP requests. Requires JavaScript-enabled "
            "browser (Playwright/Selenium)."
        )
        raise ScraperError(
            self.scraper_id,
            "Site blocked by Cloudflare challenge - requires JavaScript execution",
            "https://jobs.fisheries.org",
        )

    def parse(self, raw_data: str) -> list[Job]:
        """
        Not implemented - site requires JavaScript.

        This method will never be called since search() raises an error.
        """
        logger.error("AFS scraper parse() called - should not happen")
        return []
