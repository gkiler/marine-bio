"""
Mote Marine Laboratory job scraper.

Scrapes: https://mote.org/about/employment-opportunities
High priority: Florida-based marine research institution.

NOTE: This site requires JavaScript rendering. Selectors are best-guess patterns.
The page loads with heading "Current Open Positions:" but job listings are dynamically loaded.
"""

import logging
from datetime import datetime

from bs4 import BeautifulSoup

from core.schemas import Job
from scrapers.base_scraper import BaseScraper
from scrapers.scraper_manager import register_scraper

logger = logging.getLogger(__name__)


@register_scraper
class MoteScraper(BaseScraper):
    """
    Scraper for Mote Marine Laboratory employment opportunities.

    Flow:
    1. Fetch employment page
    2. Parse job listings from research institution
    3. Extract position details and application links
    """

    scraper_id = "mote"

    def search(self, query_params: dict | None = None) -> str:
        """Fetch Mote employment page HTML."""
        url = "https://mote.org/about/employment-opportunities"
        response = self.fetch(url)
        return response.text

    def parse(self, raw_data: str) -> list[Job]:
        """
        Parse Mote Marine job listings from HTML.

        Extracts job postings for marine research positions.
        Handles missing fields gracefully.
        """
        soup = BeautifulSoup(raw_data, "lxml")
        jobs = []

        # Look for job listing patterns - research institutions often use tables or lists
        job_cards = (
            soup.find_all("div", class_=lambda x: x and ("job" in x.lower() or "position" in x.lower() or "opening" in x.lower()) if x else False)
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

                # Skip if this doesn't look like a job title
                if len(title) < 5 or title.lower() in ["jobs", "positions", "opportunities"]:
                    continue

                # Extract URL
                link_elem = card.find("a", href=True)
                if link_elem:
                    url = link_elem["href"]
                    if not url.startswith("http"):
                        url = f"https://mote.org{url}"
                else:
                    # If no link, use the main page
                    url = "https://mote.org/about/employment-opportunities"

                # Mote is the employer
                employer = "Mote Marine Laboratory"

                # Location is primarily Sarasota, FL
                location_city = "Sarasota"
                location_state = "FL"

                # Extract description
                description_elem = (
                    card.find("p")
                    or card.find("div", class_=lambda x: x and "description" in x.lower() if x else False)
                    or card.find_next_sibling("p")
                )
                description = description_elem.get_text(strip=True) if description_elem else f"Marine research position at Mote Marine Laboratory in Sarasota, FL. {title}"

                # Determine job type from title
                job_type = "full-time"
                title_lower = title.lower()
                if "intern" in title_lower:
                    job_type = "internship"
                elif "volunteer" in title_lower:
                    job_type = "volunteer"
                elif "part-time" in title_lower or "part time" in title_lower:
                    job_type = "part-time"
                elif "seasonal" in title_lower:
                    job_type = "seasonal"

                job = Job(
                    job_id=f"mote_{idx}_{hash(title) % 100000}",
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
                logger.warning("Failed to parse Mote job card %d: %s", idx, e)
                continue

        logger.info("Mote scraper parsed %d jobs", len(jobs))
        return jobs
