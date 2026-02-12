"""
Wildlife Conservation Society careers scraper.

BLOCKED: WCS uses IBM Kenexa BrassRing applicant tracking system with Angular-based
job rendering. The static HTML contains Angular templates ({{job.Link}}, ng-* attributes)
and placeholders, but no actual job content.

This scraper is disabled and will return 0 jobs until a JavaScript-enabled solution
(Playwright, Selenium) is implemented.

Verified blocking on 2026-02-12:
- Site uses BrassRing ATS (sjobs.brassring.com)
- Angular templates throughout (e.g., {{job.Link}}, ng-controller)
- 29 job-related divs but all contain template syntax, not actual data
- Jobs load dynamically after Angular initializes
"""

import logging

from core.exceptions import ScraperError
from core.schemas import Job
from scrapers.base_scraper import BaseScraper
from scrapers.scraper_manager import register_scraper

logger = logging.getLogger(__name__)


@register_scraper
class WcsScraper(BaseScraper):
    """
    Scraper for Wildlife Conservation Society job listings.

    Currently disabled due to BrassRing Angular rendering.
    """

    scraper_id = "wcs"

    def search(self, query_params: dict | None = None) -> str:
        """
        WCS uses IBM Kenexa BrassRing ATS that requires JavaScript execution.

        Raises ScraperError to indicate the site is not scrapable without JS.
        """
        logger.warning(
            "WCS scraper is disabled: site uses IBM Kenexa BrassRing ATS with Angular "
            "that renders all content client-side. Requires JavaScript-enabled browser (Playwright/Selenium)."
        )
        raise ScraperError(
            self.scraper_id,
            "Site requires JavaScript execution - IBM Kenexa BrassRing ATS with Angular",
            "https://sjobs.brassring.com/TGnewUI/Search/Home/Home?partnerid=25965&siteid=5168",
        )

    def parse(self, raw_data: str) -> list[Job]:
        """
        Not implemented - site requires JavaScript.

        This method will never be called since search() raises an error.
        """
        return []
