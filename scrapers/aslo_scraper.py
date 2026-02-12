"""
Association for the Sciences of Limnology and Oceanography job scraper.

BLOCKED: ASLO career center is on MemberSuite platform which renders a
generic "Member Portal" landing page. No job content is visible without
what appears to be membership authentication.

Tested 2026-02-12 with Playwright:
- Rendered 503k chars but page shows only "Welcome!" and meeting info
- No job-related links or content anywhere in DOM
- Cookie consent overlay present
- Likely requires membership login to access career center

This scraper remains disabled. Would need ASLO member credentials to access.
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

    Disabled: MemberSuite platform requires membership login.
    """

    scraper_id = "aslo"

    def search(self, query_params: dict | None = None) -> str:
        """Disabled — requires membership login (MemberSuite platform)."""
        raise ScraperError(
            self.scraper_id,
            "Career center requires membership login (MemberSuite platform)",
            "http://aslo.users.membersuite.com/community/career-center/browse-jobs",
        )

    def parse(self, raw_data: str) -> list[Job]:
        """Not implemented — search() raises."""
        return []
