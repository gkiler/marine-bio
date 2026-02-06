"""
Conservation Job Board scraper (HTML).

Scrapes marine biology job listings from Conservation Job Board.
"""

import logging

from bs4 import BeautifulSoup

from core.schemas import Job
from scrapers.base_scraper import BaseScraper
from scrapers.scraper_manager import register_scraper

logger = logging.getLogger(__name__)


@register_scraper
class ConservationScraper(BaseScraper):
    """Scraper for Conservation Job Board marine biology category."""

    scraper_id = "conservation"

    def search(self, query_params: dict | None = None) -> str:
        """Fetch the Conservation Job Board marine biology jobs page."""
        url = "https://www.conservationjobboard.com/category/marine-biology-jobs"
        response = self.fetch(url)
        return response.text

    def parse(self, raw_data: str) -> list[Job]:
        """
        Parse job listings from Conservation Job Board.

        Assumes job cards with title, employer, location, and link.
        """
        soup = BeautifulSoup(raw_data, "lxml")
        jobs = []

        # Look for job listing elements
        # Try common patterns for job boards
        job_elements = soup.find_all("article", class_=lambda x: x and "job" in x.lower()) or \
                       soup.find_all("div", class_=lambda x: x and "job-listing" in x.lower()) or \
                       soup.find_all("li", class_=lambda x: x and "job" in x.lower())

        if not job_elements:
            logger.warning("Conservation Job Board: No job elements found")
            return jobs

        for element in job_elements:
            try:
                # Extract title and URL
                title_elem = element.find("h2") or element.find("h3") or element.find("a", class_=lambda x: x and "title" in x.lower())
                if not title_elem:
                    continue

                title = title_elem.get_text(strip=True)

                # Get URL
                link_elem = title_elem.find("a") if title_elem.name != "a" else title_elem
                if not link_elem or not link_elem.get("href"):
                    continue

                url = link_elem["href"]
                if url.startswith("/"):
                    url = f"https://www.conservationjobboard.com{url}"

                # Extract employer
                employer_elem = element.find(class_=lambda x: x and ("company" in x.lower() or "employer" in x.lower()))
                employer = employer_elem.get_text(strip=True) if employer_elem else "Unknown Employer"

                # Extract location
                location_elem = element.find(class_=lambda x: x and "location" in x.lower())
                location_city = None
                location_state = None
                if location_elem:
                    location_text = location_elem.get_text(strip=True)
                    # Try to parse "City, State" format
                    parts = location_text.split(",")
                    if len(parts) >= 2:
                        location_city = parts[0].strip()
                        location_state = parts[1].strip()

                # Extract description
                desc_elem = element.find("p") or element.find("div", class_=lambda x: x and "description" in x.lower())
                description = desc_elem.get_text(strip=True) if desc_elem else "See job posting for details"

                # Generate unique ID
                job_id = f"conservation_{hash(url) % 1000000}"

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
                logger.error("Error parsing Conservation Job Board job: %s", e)
                continue

        logger.info("Parsed %d jobs from Conservation Job Board", len(jobs))
        return jobs
