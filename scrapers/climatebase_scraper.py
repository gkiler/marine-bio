# NOTE: Site times out and likely requires JavaScript rendering. Selectors are best-guess.
"""
Climatebase marine/ocean jobs scraper (HTML).

Scrapes climate jobs from Climatebase, filtering for marine/ocean positions.
"""

import logging

from bs4 import BeautifulSoup

from core.schemas import Job
from scrapers.base_scraper import BaseScraper
from scrapers.scraper_manager import register_scraper

logger = logging.getLogger(__name__)


@register_scraper
class ClimatebaseScraper(BaseScraper):
    """Scraper for Climatebase marine/ocean jobs."""

    scraper_id = "climatebase"

    def search(self, query_params: dict | None = None) -> str:
        """
        Fetch Climatebase jobs page.

        Note: May need to search for marine/ocean keywords or filter by category.
        Using homepage for now, can add search params later.
        """
        url = "https://climatebase.org"
        response = self.fetch(url)
        return response.text

    def parse(self, raw_data: str) -> list[Job]:
        """
        Parse job listings from Climatebase.

        Filters for marine/ocean related positions.
        """
        soup = BeautifulSoup(raw_data, "lxml")
        jobs = []

        # Look for job listing elements
        job_elements = soup.find_all("div", class_=lambda x: x and "job" in x.lower()) or \
                       soup.find_all("article") or \
                       soup.find_all("a", class_=lambda x: x and "listing" in x.lower())

        if not job_elements:
            logger.warning("Climatebase: No job elements found")
            return jobs

        # Keywords to filter for marine/ocean jobs
        marine_keywords = ["marine", "ocean", "fisheries", "aquatic", "coastal", "sea", "reef"]

        for element in job_elements:
            try:
                # Extract title
                title_elem = element.find("h2") or element.find("h3") or element.find("span", class_=lambda x: x and "title" in x.lower())
                if not title_elem:
                    continue

                title = title_elem.get_text(strip=True)

                # Filter for marine/ocean jobs
                title_lower = title.lower()
                if not any(keyword in title_lower for keyword in marine_keywords):
                    # Check description too if available
                    desc_elem = element.find("p") or element.find("div", class_=lambda x: x and "description" in x.lower())
                    if desc_elem:
                        desc_lower = desc_elem.get_text(strip=True).lower()
                        if not any(keyword in desc_lower for keyword in marine_keywords):
                            continue
                    else:
                        continue

                # Get URL
                link_elem = element.find("a") or (element if element.name == "a" else None)
                if not link_elem or not link_elem.get("href"):
                    continue

                url = link_elem["href"]
                if url.startswith("/"):
                    url = f"https://climatebase.org{url}"

                # Extract employer
                employer_elem = element.find(class_=lambda x: x and ("company" in x.lower() or "employer" in x.lower()))
                employer = employer_elem.get_text(strip=True) if employer_elem else "Unknown Employer"

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

                # Generate unique ID
                job_id = f"climatebase_{hash(url) % 1000000}"

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
                    job_type="full-time",
                    posted_date=None,
                    application_deadline=None,
                    url=url,
                    source=self.scraper_id,
                )
                jobs.append(job)

            except Exception as e:
                logger.error("Error parsing Climatebase job: %s", e)
                continue

        logger.info("Parsed %d marine/ocean jobs from Climatebase", len(jobs))
        return jobs
