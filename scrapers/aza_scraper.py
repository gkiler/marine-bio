"""
AZA (Association of Zoos and Aquariums) job scraper.

Scrapes: https://www.aza.org/jobs
"""

import logging
from datetime import datetime

from bs4 import BeautifulSoup

from core.schemas import Job
from scrapers.base_scraper import BaseScraper
from scrapers.scraper_manager import register_scraper

logger = logging.getLogger(__name__)


@register_scraper
class AZAScraper(BaseScraper):
    """
    Scraper for Association of Zoos and Aquariums job board.

    Flow:
    1. Fetch job listings page
    2. Parse job cards for title, employer, location
    3. Extract job URLs and metadata
    """

    scraper_id = "aza"

    def search(self, query_params: dict | None = None) -> str:
        """Fetch AZA jobs page HTML."""
        url = "https://www.aza.org/jobs"
        response = self.fetch(url)
        return response.text

    def parse(self, raw_data: str) -> list[Job]:
        """
        Parse AZA job listings from HTML.

        Extracts job cards with title, employer, location, and URL.
        Handles missing fields gracefully.
        """
        soup = BeautifulSoup(raw_data, "lxml")
        jobs = []

        # Look for common job listing patterns
        # Try multiple selectors as the exact structure is unknown
        job_cards = (
            soup.find_all("div", class_=lambda x: x and "job" in x.lower())
            or soup.find_all("article", class_=lambda x: x and "job" in x.lower())
            or soup.find_all("li", class_=lambda x: x and "job" in x.lower())
        )

        for idx, card in enumerate(job_cards):
            try:
                # Extract title
                title_elem = (
                    card.find("h2")
                    or card.find("h3")
                    or card.find("a", class_=lambda x: x and "title" in x.lower() if x else False)
                )
                if not title_elem:
                    continue

                title = title_elem.get_text(strip=True)

                # Extract URL
                link_elem = card.find("a", href=True)
                if not link_elem:
                    continue
                url = link_elem["href"]
                if not url.startswith("http"):
                    url = f"https://www.aza.org{url}"

                # Extract employer
                employer_elem = card.find(class_=lambda x: x and ("employer" in x.lower() or "organization" in x.lower()) if x else False)
                employer = employer_elem.get_text(strip=True) if employer_elem else "AZA Member"

                # Extract location
                location_elem = card.find(class_=lambda x: x and "location" in x.lower() if x else False)
                location_text = location_elem.get_text(strip=True) if location_elem else None

                location_city = None
                location_state = None
                if location_text:
                    parts = [p.strip() for p in location_text.split(",")]
                    if len(parts) >= 2:
                        location_city = parts[0]
                        location_state = parts[1]
                    elif len(parts) == 1:
                        location_state = parts[0]

                # Extract description (snippet if available)
                description_elem = card.find("p") or card.find("div", class_=lambda x: x and "description" in x.lower() if x else False)
                description = description_elem.get_text(strip=True) if description_elem else "Job details available on AZA website"

                job = Job(
                    job_id=f"aza_{idx}_{hash(url) % 100000}",
                    title=title,
                    employer=employer,
                    location_city=location_city,
                    location_state=location_state,
                    location_country="USA",
                    remote=False,
                    description=description,
                    requirements=[],
                    salary_range=None,
                    job_type="full-time",
                    posted_date=None,
                    application_deadline=None,
                    url=url,
                    source=self.scraper_id,
                )

                jobs.append(job)

            except Exception as e:
                logger.warning("Failed to parse AZA job card %d: %s", idx, e)
                continue

        logger.info("AZA scraper parsed %d jobs", len(jobs))
        return jobs
