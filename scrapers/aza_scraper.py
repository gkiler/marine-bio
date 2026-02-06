"""
AZA (Association of Zoos and Aquariums) job scraper.

Scrapes: https://www.aza.org/jobs
"""

import logging
from datetime import datetime

from bs4 import BeautifulSoup

from core.schemas import Job
from scrapers.base_scraper import BaseScraper
from scrapers.scraper_manager import register_scraper

logger = logging.getLogger(__name__)


@register_scraper
class AZAScraper(BaseScraper):
    """
    Scraper for Association of Zoos and Aquariums job board.

    Flow:
    1. Fetch job listings page
    2. Parse job cards for title, employer, location
    3. Extract job URLs and metadata
    """

    scraper_id = "aza"

    def search(self, query_params: dict | None = None) -> str:
        """Fetch AZA jobs page HTML."""
        url = "https://www.aza.org/jobs"
        response = self.fetch(url)
        return response.text

    def parse(self, raw_data: str) -> list[Job]:
        """
        Parse AZA job listings from HTML.

        Verified structure (2026-02):
          table.jobs-list > tr (skip header row)
            td[0]: a.job-posting-title (has href="?job=XXXXX"), span.job-posting-company
            td[1]: span.job-posting-location
            td[2]: span.job-posting-date
            td[3]: span.job-posting-member-organization
        """
        soup = BeautifulSoup(raw_data, "lxml")
        jobs = []

        # Find the jobs table
        table = soup.find("table", class_="jobs-list")
        if not table:
            logger.warning("AZA: No table.jobs-list found")
            return jobs

        rows = table.find_all("tr")[1:]  # Skip header row
        logger.info("AZA: Found %d job rows", len(rows))

        for row in rows:
            try:
                cells = row.find_all("td")
                if len(cells) < 3:
                    continue

                # Cell 0: Title + Employer
                title_link = cells[0].find("a", class_="job-posting-title")
                if not title_link:
                    continue

                title = title_link.get_text(strip=True)
                job_href = title_link.get("href", "")

                # Extract job ID from href (e.g., "?job=50133")
                job_num = job_href.split("=")[-1] if "=" in job_href else hash(job_href) % 1000000
                job_id = f"aza_{job_num}"

                # Full URL
                url = f"https://www.aza.org/jobs{job_href}" if job_href.startswith("?") else job_href

                # Employer
                employer_span = cells[0].find("span", class_="job-posting-company")
                employer = employer_span.get_text(strip=True) if employer_span else "AZA Member"

                # Cell 1: Location
                location_span = cells[1].find("span", class_="job-posting-location")
                location_text = location_span.get_text(strip=True) if location_span else ""

                location_city = None
                location_state = None
                if location_text:
                    parts = [p.strip() for p in location_text.split(",")]
                    if len(parts) >= 2:
                        location_city = parts[0]
                        location_state = parts[1]
                    elif len(parts) == 1:
                        location_state = parts[0]

                # Cell 2: Posted date
                date_span = cells[2].find("span", class_="job-posting-date")
                date_text = date_span.get_text(strip=True) if date_span else ""

                # Try to parse date (format: "Feb 05, 2026")
                posted_date = None
                if date_text:
                    try:
                        posted_date = datetime.strptime(date_text, "%b %d, %Y")
                    except ValueError:
                        pass

                job = Job(
                    job_id=job_id,
                    title=title,
                    employer=employer,
                    location_city=location_city,
                    location_state=location_state,
                    location_country="USA",
                    remote=False,
                    description=f"{title} at {employer}. Posted {date_text}.",
                    requirements=[],
                    salary_range=None,
                    job_type="full-time",
                    posted_date=posted_date,
                    application_deadline=None,
                    url=url,
                    source=self.scraper_id,
                )

                jobs.append(job)

            except Exception as e:
                logger.error("Error parsing AZA job row: %s", e)
                continue

        logger.info("AZA scraper parsed %d jobs", len(jobs))
        return jobs
