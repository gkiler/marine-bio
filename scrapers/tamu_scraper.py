"""
Texas A&M Oceanography jobs scraper (HTML).

Scrapes job listings from Texas A&M University's oceanography department.
"""

import logging

from bs4 import BeautifulSoup

from core.schemas import Job
from scrapers.base_scraper import BaseScraper
from scrapers.scraper_manager import register_scraper

logger = logging.getLogger(__name__)


@register_scraper
class TAMUScraper(BaseScraper):
    """Scraper for Texas A&M Oceanography jobs."""

    scraper_id = "tamu"

    def search(self, query_params: dict | None = None) -> str:
        """Fetch the Texas A&M oceanography jobs/careers page."""
        url = "https://ocean.tamu.edu"
        response = self.fetch(url)
        return response.text

    def parse(self, raw_data: str) -> list[Job]:
        """
        Parse job listings from Texas A&M Oceanography.

        Academic job boards typically have position announcements.
        """
        soup = BeautifulSoup(raw_data, "lxml")
        jobs = []

        # Look for job/position listings - try multiple selectors
        job_elements = soup.find_all("div", class_=lambda x: x and ("job" in x.lower() or "position" in x.lower())) or \
                       soup.find_all("article") or \
                       soup.find_all("li", class_=lambda x: x and "career" in x.lower())

        if not job_elements:
            # Try finding links with job-related keywords in text
            links = soup.find_all("a", string=lambda x: x and any(word in x.lower() for word in ["position", "job", "opening", "hiring"]))
            if links:
                job_elements = [link.parent for link in links]

        if not job_elements:
            logger.warning("Texas A&M: No job elements found")
            return jobs

        for element in job_elements:
            try:
                # Extract title
                title_elem = element.find("h2") or element.find("h3") or element.find("a", class_=lambda x: x and "title" in x.lower())
                if not title_elem:
                    # Try finding any link with substantial text
                    title_elem = element.find("a")
                if not title_elem:
                    continue

                title = title_elem.get_text(strip=True)

                # Get URL
                link_elem = title_elem.find("a") if title_elem.name != "a" else title_elem
                if not link_elem or not link_elem.get("href"):
                    continue

                url = link_elem["href"]
                if url.startswith("/"):
                    url = f"https://ocean.tamu.edu{url}"

                # Employer is Texas A&M
                employer = "Texas A&M University - Oceanography"

                # Location is College Station, TX
                location_city = "College Station"
                location_state = "TX"

                # Extract description
                desc_elem = element.find("p") or element.find("div", class_=lambda x: x and "description" in x.lower())
                description = desc_elem.get_text(strip=True) if desc_elem else "See job posting for details"

                # Generate unique ID
                job_id = f"tamu_{hash(url) % 1000000}"

                job = Job(
                    job_id=job_id,
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
                logger.error("Error parsing Texas A&M job: %s", e)
                continue

        logger.info("Parsed %d jobs from Texas A&M Oceanography", len(jobs))
        return jobs
