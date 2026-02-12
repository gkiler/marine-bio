"""
Seven Seas Media ocean jobs scraper.

BLOCKED: Seven Seas Media uses WordPress Job Manager plugin with AJAX-based job loading.
The static HTML contains the job board framework but all actual job listings are loaded
dynamically via JavaScript/AJAX after page load.

This scraper is disabled and will return 0 jobs until a JavaScript-enabled solution
(Playwright, Selenium) is implemented.

Verified blocking on 2026-02-12:
- Site uses WP Job Manager with AJAX job loading
- Static HTML has <div class="job_listings"> but no <li> job items
- Job data-per_page="10" indicates AJAX pagination
- No job content in initial page load
"""

import logging

from core.exceptions import ScraperError
from core.schemas import Job
from scrapers.base_scraper import BaseScraper
from scrapers.scraper_manager import register_scraper

logger = logging.getLogger(__name__)


@register_scraper
class SevenSeasScraper(BaseScraper):
    """
    Scraper for Seven Seas Media ocean jobs.

    Currently disabled due to WordPress Job Manager AJAX rendering.
    """

    scraper_id = "sevenseas"

    def search(self, query_params: dict | None = None) -> str:
        """
        Seven Seas Media uses WordPress Job Manager with AJAX-loaded jobs.

        Raises ScraperError to indicate the site is not scrapable without JS.
        """
        logger.warning(
            "Seven Seas Media scraper is disabled: site uses WordPress Job Manager "
            "that loads all jobs via AJAX. Requires JavaScript-enabled browser (Playwright/Selenium)."
        )
        raise ScraperError(
            self.scraper_id,
            "Site requires JavaScript execution - WordPress Job Manager with AJAX loading",
            "https://sevenseasmedia.org/ocean-jobs",
        )

    def parse(self, raw_data: str) -> list[Job]:
        """
        Not implemented - site requires JavaScript.

        This method will never be called since search() raises an error.
        """
        return []
