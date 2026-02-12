"""
Academic scraper - higheredjobs.com (higher education jobs)

BLOCKED: HigherEdJobs uses PerimeterX bot detection that blocks even
headless Playwright browsers. The site returns a minimal challenge page
(~1068 chars) with no job content.

Tested 2026-02-12 with Playwright:
- Page timed out during render (45s)
- Only 1068 chars captured — bot detection challenge page
- No job content in DOM at all
- Neither httpx nor Playwright can bypass PerimeterX

This scraper remains disabled. Would need playwright-stealth or a
residential proxy to bypass bot detection.
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

    Disabled: PerimeterX bot detection blocks all automated access.
    """

    scraper_id = "academic"

    def search(self, query_params: dict | None = None) -> str:
        """Disabled — PerimeterX bot detection blocks automated access."""
        raise ScraperError(
            self.scraper_id,
            "Site blocked by PerimeterX bot detection",
            "https://www.higheredjobs.com/",
        )

    def parse(self, raw_data: str) -> list[Job]:
        """Not implemented — search() raises."""
        return []
