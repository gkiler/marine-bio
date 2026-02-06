"""
NOAA Fisheries careers page scraper (HTML).

Scrapes job listings from the NOAA Fisheries careers page.
"""

import logging

from bs4 import BeautifulSoup

from core.schemas import Job
from scrapers.base_scraper import BaseScraper
from scrapers.scraper_manager import register_scraper

logger = logging.getLogger(__name__)


@register_scraper
class NOAAScraper(BaseScraper):
    """Scraper for NOAA Fisheries careers page."""

    scraper_id = "noaa"

    def search(self, query_params: dict | None = None) -> str:
        """Fetch the NOAA careers page HTML."""
        url = "https://www.fisheries.noaa.gov/topic/careers-more"
        response = self.fetch(url)
        return response.text

    def parse(self, raw_data: str) -> list[Job]:
        """
        Parse job listings from NOAA careers page.

        Assumes job cards/listings with title, link, and description.
        Exact structure unknown, using common patterns for government job boards.
        """
        soup = BeautifulSoup(raw_data, "lxml")
        jobs = []

        # Look for article elements or common job listing containers
        # Try multiple selectors since we don't know the exact structure
        job_elements = soup.find_all("article", class_=lambda x: x and "job" in x.lower()) or \
                       soup.find_all("div", class_=lambda x: x and "career" in x.lower()) or \
                       soup.find_all("div", class_=lambda x: x and "listing" in x.lower())

        if not job_elements:
            logger.warning("NOAA: No job elements found on page")
            return jobs

        for idx, element in enumerate(job_elements):
            try:
                # Extract title - try multiple patterns
                title_elem = element.find("h2") or element.find("h3") or element.find("a", class_=lambda x: x and "title" in x.lower())
                if not title_elem:
                    continue

                title = title_elem.get_text(strip=True)

                # Extract URL - look for link in title or element
                link_elem = title_elem.find("a") if title_elem.name != "a" else title_elem
                if not link_elem or not link_elem.get("href"):
                    continue

                url = link_elem["href"]
                # Make URL absolute if relative
                if url.startswith("/"):
                    url = f"https://www.fisheries.noaa.gov{url}"

                # Extract description
                desc_elem = element.find("p") or element.find("div", class_=lambda x: x and "description" in x.lower())
                description = desc_elem.get_text(strip=True) if desc_elem else "See job posting for details"

                # Generate unique ID
                job_id = f"noaa_{hash(url) % 1000000}"

                job = Job(
                    job_id=job_id,
                    title=title,
                    employer="NOAA Fisheries",
                    location_city=None,
                    location_state=None,
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
                logger.error("Error parsing NOAA job element: %s", e)
                continue

        logger.info("Parsed %d jobs from NOAA", len(jobs))
        return jobs
