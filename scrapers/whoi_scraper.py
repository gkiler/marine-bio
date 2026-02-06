"""
Woods Hole Oceanographic Institution job scraper.

Scrapes: https://careers.whoi.edu

NOTE: This site uses Workday ATS (external system at https://whoi.wd5.myworkdayjobs.com/WHOI-External).
The main careers page redirects to Workday, which requires JavaScript rendering.
Selectors are best-guess patterns.
"""

import logging
from datetime import datetime

from bs4 import BeautifulSoup

from core.schemas import Job
from scrapers.base_scraper import BaseScraper
from scrapers.scraper_manager import register_scraper

logger = logging.getLogger(__name__)


@register_scraper
class WHOIScraper(BaseScraper):
    """
    Scraper for Woods Hole Oceanographic Institution careers.

    Flow:
    1. Fetch careers page
    2. Parse research and technical positions
    3. Extract job details and application links
    """

    scraper_id = "whoi"

    def search(self, query_params: dict | None = None) -> str:
        """Fetch WHOI careers page HTML."""
        url = "https://careers.whoi.edu"
        response = self.fetch(url)
        return response.text

    def parse(self, raw_data: str) -> list[Job]:
        """
        Parse WHOI job listings from HTML.

        Extracts oceanographic research positions.
        Handles missing fields gracefully.
        """
        soup = BeautifulSoup(raw_data, "lxml")
        jobs = []

        # Look for job listing patterns
        job_cards = (
            soup.find_all("div", class_=lambda x: x and ("job" in x.lower() or "position" in x.lower() or "posting" in x.lower()) if x else False)
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
                    or card.find("td", class_=lambda x: x and "title" in x.lower() if x else False)
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
                        url = f"https://careers.whoi.edu{url}"
                else:
                    url = "https://careers.whoi.edu"

                # WHOI is the employer
                employer = "Woods Hole Oceanographic Institution"

                # Location is Woods Hole, MA
                location_city = "Woods Hole"
                location_state = "MA"

                # Extract description
                description_elem = (
                    card.find("p")
                    or card.find("div", class_=lambda x: x and "description" in x.lower() if x else False)
                    or card.find("td", class_=lambda x: x and "description" in x.lower() if x else False)
                )
                description = description_elem.get_text(strip=True) if description_elem else f"Oceanographic research position at Woods Hole. {title}"

                # Extract posted date if available
                date_elem = card.find(class_=lambda x: x and ("date" in x.lower() or "posted" in x.lower()) if x else False)
                posted_date = None
                if date_elem:
                    try:
                        date_text = date_elem.get_text(strip=True)
                        # Try basic parsing - this would need adjustment based on actual format
                        posted_date = datetime.strptime(date_text, "%m/%d/%Y")
                    except Exception:
                        posted_date = None

                # Determine job type
                job_type = "full-time"
                title_lower = title.lower()
                if "intern" in title_lower:
                    job_type = "internship"
                elif "volunteer" in title_lower or "fellow" in title_lower:
                    job_type = "volunteer"
                elif "part-time" in title_lower or "part time" in title_lower:
                    job_type = "part-time"
                elif "seasonal" in title_lower or "summer" in title_lower:
                    job_type = "seasonal"

                job = Job(
                    job_id=f"whoi_{idx}_{hash(url) % 100000}",
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
                    posted_date=posted_date,
                    application_deadline=None,
                    url=url,
                    source=self.scraper_id,
                )

                jobs.append(job)

            except Exception as e:
                logger.warning("Failed to parse WHOI job card %d: %s", idx, e)
                continue

        logger.info("WHOI scraper parsed %d jobs", len(jobs))
        return jobs
