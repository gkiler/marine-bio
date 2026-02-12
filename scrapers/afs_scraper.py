"""
American Fisheries Society job scraper.

BLOCKED: jobs.fisheries.org uses Cloudflare JavaScript challenge that
blocks even headless Playwright browsers. The page returns the "Just a
moment..." challenge and never resolves to actual content.

Tested 2026-02-12 with Playwright:
- Page timed out during render (45s)
- Captured 27k chars — all Cloudflare challenge HTML
- Page title: "Just a moment..."
- No job content anywhere in DOM
- Cloudflare detects headless browser despite Playwright

To potentially fix: try playwright-stealth plugin, but Cloudflare detection
is increasingly resistant to stealth techniques. May need residential proxy
or manual RSS/API approach.
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

    Disabled: Cloudflare challenge blocks all automated access.
    """

    scraper_id = "afs"

    def search(self, query_params: dict | None = None) -> str:
        """Disabled — Cloudflare JavaScript challenge blocks access."""
        raise ScraperError(
            self.scraper_id,
            "Site blocked by Cloudflare challenge",
            "https://jobs.fisheries.org",
        )

    def parse(self, raw_data: str) -> list[Job]:
        """Not implemented — search() raises."""
        return []
