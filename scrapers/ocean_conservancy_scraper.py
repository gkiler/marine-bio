"""
Ocean Conservancy jobs scraper.

BLOCKED: Ocean Conservancy uses ADP Workforce Now, a third-party applicant tracking
system (ATS) that requires JavaScript execution. The site returns only a minimal HTML
page with a message to enable JavaScript.

This scraper is disabled and will return 0 jobs until a JavaScript-enabled solution
(Playwright, Selenium) is implemented.

Verified blocking on 2026-02-12:
- Redirects to ADP Workforce Now portal
- Body contains only 95 chars: "Please switch to a supported browser..."
- All job content requires JavaScript
- ADP URL: https://workforcenow.adp.com/mascsr/default/mdf/recruitment/...
"""

import logging

from core.exceptions import ScraperError
from core.schemas import Job
from scrapers.base_scraper import BaseScraper
from scrapers.scraper_manager import register_scraper

logger = logging.getLogger(__name__)


@register_scraper
class OceanConservancyScraper(BaseScraper):
    """
    Scraper for Ocean Conservancy job listings.

    Currently disabled due to ADP Workforce Now JavaScript requirement.
    """

    scraper_id = "ocean_conservancy"

    def search(self, query_params: dict | None = None) -> str:
        """
        Ocean Conservancy uses ADP Workforce Now that requires JavaScript execution.

        Raises ScraperError to indicate the site is not scrapable without JS.
        """
        logger.warning(
            "Ocean Conservancy scraper is disabled: site uses ADP Workforce Now ATS "
            "that requires JavaScript execution. Requires JavaScript-enabled browser (Playwright/Selenium)."
        )
        raise ScraperError(
            self.scraper_id,
            "Site requires JavaScript execution - ADP Workforce Now ATS",
            "https://workforcenow.adp.com/mascsr/default/mdf/recruitment/recruitment.html?cid=4786a4ca-9800-4db8-98cb-8bc9baad2b0d",
        )

    def parse(self, raw_data: str) -> list[Job]:
        """
        Not implemented - site requires JavaScript.

        This method will never be called since search() raises an error.
        """
        return []
