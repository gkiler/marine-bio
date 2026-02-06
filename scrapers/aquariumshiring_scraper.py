"""
AquariumsHiring.com job scraper.

Scrapes: https://www.aquariumshiring.com
"""

import logging
from datetime import datetime

from bs4 import BeautifulSoup

from core.schemas import Job
from scrapers.base_scraper import BaseScraper
from scrapers.scraper_manager import register_scraper

logger = logging.getLogger(__name__)


@register_scraper
class AquariumsHiringScraper(BaseScraper):
    """
    Scraper for AquariumsHiring.com job board.

    Flow:
    1. Fetch job listings page
    2. Parse job postings for aquarium positions
    3. Extract metadata and links
    """

    scraper_id = "aquariumshiring"

    def search(self, query_params: dict | None = None) -> str:
        """Fetch AquariumsHiring.com page HTML."""
        url = "https://www.aquariumshiring.com"
        response = self.fetch(url)
        return response.text

    def parse(self, raw_data: str) -> list[Job]:
        """
        Parse aquarium job listings from HTML.

        Extracts job cards with title, employer, location, and URL.
        Handles missing fields gracefully.
        """
        soup = BeautifulSoup(raw_data, "lxml")
        jobs = []

        # Look for job listing patterns
        job_cards = (
            soup.find_all("div", class_=lambda x: x and "job" in x.lower())
            or soup.find_all("article")
            or soup.find_all("li", class_=lambda x: x and ("posting" in x.lower() or "listing" in x.lower()) if x else False)
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

                # Extract URL
                link_elem = card.find("a", href=True)
                if not link_elem:
                    continue
                url = link_elem["href"]
                if not url.startswith("http"):
                    url = f"https://www.aquariumshiring.com{url}"

                # Extract employer (aquarium name)
                employer_elem = (
                    card.find(class_=lambda x: x and ("employer" in x.lower() or "aquarium" in x.lower() or "facility" in x.lower()) if x else False)
                    or card.find("strong")
                )
                employer = employer_elem.get_text(strip=True) if employer_elem else "Aquarium"

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

                # Extract description
                description_elem = (
                    card.find("p")
                    or card.find("div", class_=lambda x: x and "description" in x.lower() if x else False)
                )
                description = description_elem.get_text(strip=True) if description_elem else "Aquarium position details available online"

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
                    job_id=f"aquariumshiring_{idx}_{hash(url) % 100000}",
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
                logger.warning("Failed to parse AquariumsHiring job card %d: %s", idx, e)
                continue

        logger.info("AquariumsHiring scraper parsed %d jobs", len(jobs))
        return jobs
