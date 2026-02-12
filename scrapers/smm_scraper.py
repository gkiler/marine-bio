"""
Society for Marine Mammalogy job scraper.

DISABLED: SMM job board has moved to:
https://marinemammalscience.org/professional-development/marine-mammal-science-job-openings/

The page contains a search form that loads jobs dynamically via JavaScript.
Jobs are not present in the initial HTML response and require form submission
or JavaScript execution to display.

To re-enable this scraper, you would need to use a JavaScript-capable scraper
like Playwright or Selenium, or reverse-engineer the backend API that the form
calls to fetch job data.
"""

import logging

from core.exceptions import ScraperError
from core.schemas import Job
from scrapers.base_scraper import BaseScraper
from scrapers.scraper_manager import register_scraper

logger = logging.getLogger(__name__)


@register_scraper
class SMMScraper(BaseScraper):
    """
    Scraper for Society for Marine Mammalogy job board.

    DISABLED: Requires JavaScript rendering (dynamic job loading via form).
    """

    scraper_id = "smm"

    def search(self, query_params: dict | None = None) -> str:
        """Raise error - scraper disabled."""
        raise ScraperError(
            scraper_id=self.scraper_id,
            message="Job board requires JavaScript rendering for dynamic job loading",
            url="https://marinemammalscience.org/professional-development/marine-mammal-science-job-openings/"
        )

    def parse(self, raw_data: str) -> list[Job]:
        """Disabled - always returns empty list."""
        return []
