"""
Idealist scraper - idealist.org (filtered by environment/science)

BLOCKED: Idealist is a React SPA. Playwright renders the page shell but the
search query parameter (?q=marine+biology&searchMode=true) does not trigger
an actual search — the page loads the generic homepage instead.

Tested 2026-02-12 with Playwright:
- Rendered 136k chars of HTML but 0 job listing links (/en/job/ pattern)
- Search requires client-side JavaScript interaction (typing in search box + submit)
- Would need Playwright page.fill() + page.click() interaction to trigger search

This scraper remains disabled. To re-enable, implement JS interaction in search().
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

    Disabled: React SPA requires JS interaction to trigger search.
    """

    scraper_id = "idealist"

    def search(self, query_params: dict | None = None) -> str:
        """Disabled — search requires JS interaction (fill + click)."""
        raise ScraperError(
            self.scraper_id,
            "Site requires JavaScript interaction to trigger search (React SPA)",
            "https://www.idealist.org/en/jobs",
        )

    def parse(self, raw_data: str) -> list[Job]:
        """Not implemented — search() raises."""
        return []
