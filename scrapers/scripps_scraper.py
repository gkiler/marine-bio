"""
Scripps Institution of Oceanography job scraper.

Scrapes: https://scripps.ucsd.edu/portal/jobs
"""

import logging
from datetime import datetime

from bs4 import BeautifulSoup

from core.schemas import Job
from scrapers.base_scraper import BaseScraper
from scrapers.scraper_manager import register_scraper

logger = logging.getLogger(__name__)


@register_scraper
class ScrippsScraper(BaseScraper):
    """
    Scraper for Scripps Institution of Oceanography jobs.

    Flow:
    1. Fetch jobs portal page
    2. Parse oceanography positions
    3. Extract job details and application links
    """

    scraper_id = "scripps"

    def search(self, query_params: dict | None = None) -> str:
        """Fetch Scripps jobs portal HTML."""
        url = "https://scripps.ucsd.edu/portal/jobs"
        response = self.fetch(url)
        return response.text

    def parse(self, raw_data: str) -> list[Job]:
        """
        Parse Scripps job listings from HTML.

        Extracts oceanographic research positions.
        Handles missing fields gracefully.
        """
        soup = BeautifulSoup(raw_data, "lxml")
        jobs = []

        # Look for job listing patterns
        job_cards = (
            soup.find_all("div", class_=lambda x: x and ("job" in x.lower() or "position" in x.lower() or "posting" in x.lower()) if x else False)
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
                )
                if not title_elem:
                    continue

                title = title_elem.get_text(strip=True)

                # Skip if not a job title
                if len(title) < 5:
                    continue

                # Extract URL
                link_elem = card.find("a", href=True)
                if link_elem:
                    url = link_elem["href"]
                    if not url.startswith("http"):
                        url = f"https://scripps.ucsd.edu{url}"
                else:
                    url = "https://scripps.ucsd.edu/portal/jobs"

                # Scripps is the employer
                employer = "Scripps Institution of Oceanography"

                # Location is La Jolla, CA (part of UCSD)
                location_city = "La Jolla"
                location_state = "CA"

                # Extract description
                description_elem = (
                    card.find("p")
                    or card.find("div", class_=lambda x: x and "description" in x.lower() if x else False)
                )
                description = description_elem.get_text(strip=True) if description_elem else f"Oceanographic research position at Scripps Institution. {title}"

                # Extract department/division if available
                dept_elem = card.find(class_=lambda x: x and ("department" in x.lower() or "division" in x.lower()) if x else False)
                if dept_elem:
                    dept_text = dept_elem.get_text(strip=True)
                    description = f"{dept_text} - {description}"

                # Determine job type
                job_type = "full-time"
                title_lower = title.lower()
                if "intern" in title_lower:
                    job_type = "internship"
                elif "postdoc" in title_lower or "fellow" in title_lower:
                    job_type = "full-time"  # Postdocs typically full-time
                elif "volunteer" in title_lower:
                    job_type = "volunteer"
                elif "part-time" in title_lower or "part time" in title_lower:
                    job_type = "part-time"
                elif "seasonal" in title_lower:
                    job_type = "seasonal"

                job = Job(
                    job_id=f"scripps_{idx}_{hash(url) % 100000}",
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
                logger.warning("Failed to parse Scripps job card %d: %s", idx, e)
                continue

        logger.info("Scripps scraper parsed %d jobs", len(jobs))
        return jobs
