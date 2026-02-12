"""
Society for Marine Mammalogy job scraper.

BLOCKED: SMM job board uses a form-based search. The page renders static
instructional text ("To browse all jobs, simply hit the Search Button")
but actual job listings only appear after submitting the search form.

Tested 2026-02-12 with Playwright:
- Rendered 56k chars but no job listing elements in DOM
- Found 2 forms and a submit button ("Search >")
- Clicking submit yields 0 headings/job elements in response
- May require specific form field values or membership access

This scraper remains disabled. To re-enable, reverse-engineer the form
submission or implement Playwright form interaction in search().
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

    Disabled: requires form interaction to load job listings.
    """

    scraper_id = "smm"

    def search(self, query_params: dict | None = None) -> str:
        """Disabled — requires form submission to load jobs."""
        raise ScraperError(
            self.scraper_id,
            "Job board requires form submission to load listings",
            "https://marinemammalscience.org/professional-development/marine-mammal-science-job-openings/",
        )

    def parse(self, raw_data: str) -> list[Job]:
        """Not implemented — search() raises."""
        return []
