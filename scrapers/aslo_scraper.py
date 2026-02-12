"""
Association for the Sciences of Limnology and Oceanography job scraper.

DISABLED: ASLO job board has moved to a JavaScript-based MemberSuite platform
at http://aslo.users.membersuite.com/community/career-center/browse-jobs/
which requires JavaScript rendering to display job listings. The page returns
static HTML with no job data in the initial response.

To re-enable this scraper, you would need to use a JavaScript-capable scraper
like Playwright or Selenium.
"""

import logging

from core.exceptions import ScraperError
from core.schemas import Job
from scrapers.base_scraper import BaseScraper
from scrapers.scraper_manager import register_scraper

logger = logging.getLogger(__name__)


@register_scraper
class ASLOScraper(BaseScraper):
    """
    Scraper for ASLO career center.

    DISABLED: Requires JavaScript rendering (MemberSuite platform).
    """

    scraper_id = "aslo"

    def search(self, query_params: dict | None = None) -> str:
        """Raise error - scraper disabled."""
        raise ScraperError(
            scraper_id=self.scraper_id,
            message="Job board requires JavaScript rendering (MemberSuite platform)",
            url="http://aslo.users.membersuite.com/community/career-center/browse-jobs"
        )

    def parse(self, raw_data: str) -> list[Job]:
        """Disabled - always returns empty list."""
        return []
