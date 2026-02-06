"""
Wise Oceans marine conservation jobs scraper (HTML).

Scrapes marine conservation job listings from Wise Oceans.
"""

import logging

from bs4 import BeautifulSoup

from core.schemas import Job
from scrapers.base_scraper import BaseScraper
from scrapers.scraper_manager import register_scraper

logger = logging.getLogger(__name__)


@register_scraper
class WiseOceansScraper(BaseScraper):
    """Scraper for Wise Oceans marine conservation jobs."""

    scraper_id = "wiseoceans"

    def search(self, query_params: dict | None = None) -> str:
        """Fetch the Wise Oceans jobs page."""
        url = "https://wiseoceans.com/jobs"
        response = self.fetch(url)
        return response.text

    def parse(self, raw_data: str) -> list[Job]:
        """
        Parse marine conservation job listings from Wise Oceans.

        Assumes job board with listing cards for conservation positions.
        """
        soup = BeautifulSoup(raw_data, "lxml")
        jobs = []

        # Look for job listing elements
        job_elements = soup.find_all("div", class_=lambda x: x and "job" in x.lower()) or \
                       soup.find_all("article") or \
                       soup.find_all("li", class_=lambda x: x and "position" in x.lower())

        if not job_elements:
            logger.warning("Wise Oceans: No job elements found")
            return jobs

        for element in job_elements:
            try:
                # Extract title
                title_elem = element.find("h2") or element.find("h3") or element.find("a", class_=lambda x: x and ("title" in x.lower() or "role" in x.lower()))
                if not title_elem:
                    continue

                title = title_elem.get_text(strip=True)

                # Get URL
                link_elem = title_elem.find("a") if title_elem.name != "a" else title_elem
                if not link_elem or not link_elem.get("href"):
                    continue

                url = link_elem["href"]
                if url.startswith("/"):
                    url = f"https://wiseoceans.com{url}"

                # Extract employer
                employer_elem = element.find(class_=lambda x: x and ("company" in x.lower() or "employer" in x.lower() or "organization" in x.lower()))
                employer = employer_elem.get_text(strip=True) if employer_elem else "Unknown Organization"

                # Extract location
                location_elem = element.find(class_=lambda x: x and "location" in x.lower())
                location_city = None
                location_state = None
                remote = False
                if location_elem:
                    location_text = location_elem.get_text(strip=True)
                    if "remote" in location_text.lower():
                        remote = True
                    parts = location_text.split(",")
                    if len(parts) >= 2:
                        location_city = parts[0].strip()
                        location_state = parts[1].strip()

                # Extract description
                desc_elem = element.find("p") or element.find("div", class_=lambda x: x and "description" in x.lower())
                description = desc_elem.get_text(strip=True) if desc_elem else "See job posting for details"

                # Job type - conservation jobs are often volunteer or internship
                job_type_elem = element.find(class_=lambda x: x and "type" in x.lower())
                job_type = "full-time"
                if job_type_elem:
                    type_text = job_type_elem.get_text(strip=True).lower()
                    if "volunteer" in type_text:
                        job_type = "volunteer"
                    elif "intern" in type_text:
                        job_type = "internship"
                    elif "part-time" in type_text or "part time" in type_text:
                        job_type = "part-time"

                # Generate unique ID
                job_id = f"wiseoceans_{hash(url) % 1000000}"

                job = Job(
                    job_id=job_id,
                    title=title,
                    employer=employer,
                    location_city=location_city,
                    location_state=location_state,
                    location_country="USA",
                    remote=remote,
                    description=description,
                    requirements=[],
                    salary_range=None,
                    job_type=job_type,
                    posted_date=None,
                    application_deadline=None,
                    url=url,
                    source=self.scraper_id,
                )
                jobs.append(job)

            except Exception as e:
                logger.error("Error parsing Wise Oceans job: %s", e)
                continue

        logger.info("Parsed %d jobs from Wise Oceans", len(jobs))
        return jobs
