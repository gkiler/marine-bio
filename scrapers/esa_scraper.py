"""
Ecological Society of America job scraper.

Scrapes: https://www.esa.org/career-center
"""

import logging
from datetime import datetime

from bs4 import BeautifulSoup

from core.schemas import Job
from scrapers.base_scraper import BaseScraper
from scrapers.scraper_manager import register_scraper

logger = logging.getLogger(__name__)


@register_scraper
class ESAScraper(BaseScraper):
    """
    Scraper for Ecological Society of America career center.

    Flow:
    1. Fetch career center page
    2. Parse ecological science positions
    3. Extract job details and application links
    """

    scraper_id = "esa"

    def search(self, query_params: dict | None = None) -> str:
        """Fetch ESA career center HTML."""
        url = "https://www.esa.org/career-center"
        response = self.fetch(url)
        return response.text

    def parse(self, raw_data: str) -> list[Job]:
        """
        Parse ESA job listings from HTML.

        Extracts ecological science positions (includes marine ecology).
        Handles missing fields gracefully.
        """
        soup = BeautifulSoup(raw_data, "lxml")
        jobs = []

        # Look for job listing patterns
        job_cards = (
            soup.find_all("div", class_=lambda x: x and ("job" in x.lower() or "posting" in x.lower() or "listing" in x.lower()) if x else False)
            or soup.find_all("tr", class_=lambda x: x and ("job" in x.lower() or "row" in x.lower()) if x else False)
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
                        url = f"https://www.esa.org{url}"
                else:
                    url = "https://www.esa.org/career-center"

                # Extract employer
                employer_elem = (
                    card.find(class_=lambda x: x and ("employer" in x.lower() or "company" in x.lower() or "organization" in x.lower()) if x else False)
                    or card.find("strong")
                )
                employer = employer_elem.get_text(strip=True) if employer_elem else "ESA Member Organization"

                # Extract location
                location_elem = card.find(class_=lambda x: x and "location" in x.lower() if x else False)
                location_text = location_elem.get_text(strip=True) if location_elem else None

                location_city = None
                location_state = None
                remote = False

                if location_text:
                    if "remote" in location_text.lower():
                        remote = True
                    parts = [p.strip() for p in location_text.replace("Remote", "").split(",")]
                    parts = [p for p in parts if p]
                    if len(parts) >= 2:
                        location_city = parts[0]
                        location_state = parts[1]
                    elif len(parts) == 1 and parts[0]:
                        location_state = parts[0]

                # Extract description
                description_elem = (
                    card.find("p")
                    or card.find("div", class_=lambda x: x and "description" in x.lower() if x else False)
                )
                description = description_elem.get_text(strip=True) if description_elem else f"Ecological science position. {title}"

                # Determine job type
                job_type = "full-time"
                title_lower = title.lower()
                desc_lower = description.lower()

                if "intern" in title_lower or "intern" in desc_lower:
                    job_type = "internship"
                elif "postdoc" in title_lower or "postdoc" in desc_lower:
                    job_type = "full-time"
                elif "volunteer" in title_lower or "volunteer" in desc_lower:
                    job_type = "volunteer"
                elif "part-time" in title_lower or "part time" in title_lower:
                    job_type = "part-time"
                elif "seasonal" in title_lower or "seasonal" in desc_lower:
                    job_type = "seasonal"

                job = Job(
                    job_id=f"esa_{idx}_{hash(url) % 100000}",
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
                logger.warning("Failed to parse ESA job card %d: %s", idx, e)
                continue

        logger.info("ESA scraper parsed %d jobs", len(jobs))
        return jobs
