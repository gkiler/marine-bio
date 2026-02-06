"""
Monterey Bay Aquarium Research Institute job scraper.

Scrapes: https://www.mbari.org/about/careers
"""

import logging
from datetime import datetime

from bs4 import BeautifulSoup

from core.schemas import Job
from scrapers.base_scraper import BaseScraper
from scrapers.scraper_manager import register_scraper

logger = logging.getLogger(__name__)


@register_scraper
class MBARIScraper(BaseScraper):
    """
    Scraper for MBARI (Monterey Bay Aquarium Research Institute) careers.

    Flow:
    1. Fetch careers page
    2. Parse marine research and engineering positions
    3. Extract job details and application links
    """

    scraper_id = "mbari"

    def search(self, query_params: dict | None = None) -> str:
        """Fetch MBARI careers page HTML."""
        url = "https://www.mbari.org/about/careers"
        response = self.fetch(url)
        return response.text

    def parse(self, raw_data: str) -> list[Job]:
        """
        Parse MBARI job listings from HTML.

        Extracts marine research positions.
        Handles missing fields gracefully.
        """
        soup = BeautifulSoup(raw_data, "lxml")
        jobs = []

        # Look for job listing patterns
        job_cards = (
            soup.find_all("div", class_=lambda x: x and ("job" in x.lower() or "position" in x.lower() or "opening" in x.lower() or "career" in x.lower()) if x else False)
            or soup.find_all("tr", class_=lambda x: x and "job" in x.lower() if x else False)
            or soup.find_all("li", class_=lambda x: x and ("job" in x.lower() or "position" in x.lower()) if x else False)
            or soup.find_all("article")
        )

        for idx, card in enumerate(job_cards):
            try:
                # Extract title
                title_elem = (
                    card.find("h2")
                    or card.find("h3")
                    or card.find("h4")
                    or card.find("a", class_=lambda x: x and "title" in x.lower() if x else False)
                    or card.find("strong")
                )
                if not title_elem:
                    continue

                title = title_elem.get_text(strip=True)

                # Skip if not a job title
                if len(title) < 5 or title.lower() in ["careers", "jobs", "openings"]:
                    continue

                # Extract URL
                link_elem = card.find("a", href=True)
                if link_elem:
                    url = link_elem["href"]
                    if not url.startswith("http"):
                        url = f"https://www.mbari.org{url}"
                else:
                    url = "https://www.mbari.org/about/careers"

                # MBARI is the employer
                employer = "Monterey Bay Aquarium Research Institute"

                # Location is Moss Landing, CA
                location_city = "Moss Landing"
                location_state = "CA"

                # Extract description
                description_elem = (
                    card.find("p")
                    or card.find("div", class_=lambda x: x and "description" in x.lower() if x else False)
                    or card.find_next_sibling("p")
                )
                description = description_elem.get_text(strip=True) if description_elem else f"Marine research position at MBARI in Moss Landing, CA. {title}"

                # Determine job type
                job_type = "full-time"
                title_lower = title.lower()
                if "intern" in title_lower:
                    job_type = "internship"
                elif "fellow" in title_lower or "postdoc" in title_lower:
                    job_type = "full-time"
                elif "volunteer" in title_lower:
                    job_type = "volunteer"
                elif "part-time" in title_lower or "part time" in title_lower:
                    job_type = "part-time"
                elif "seasonal" in title_lower or "summer" in title_lower:
                    job_type = "seasonal"

                job = Job(
                    job_id=f"mbari_{idx}_{hash(title) % 100000}",
                    title=title,
                    employer=employer,
                    location_city=location_city,
                    location_state=location_state,
                    location_country="USA",
                    remote=False,
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
                logger.warning("Failed to parse MBARI job card %d: %s", idx, e)
                continue

        logger.info("MBARI scraper parsed %d jobs", len(jobs))
        return jobs
