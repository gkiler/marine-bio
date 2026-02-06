"""
Schmidt Marine Technology Partners jobs scraper (HTML).

Scrapes job listings from Schmidt Marine's job board.
"""

import logging

from bs4 import BeautifulSoup

from core.schemas import Job
from scrapers.base_scraper import BaseScraper
from scrapers.scraper_manager import register_scraper

logger = logging.getLogger(__name__)


@register_scraper
class SchmidtScraper(BaseScraper):
    """Scraper for Schmidt Marine Technology Partners jobs."""

    scraper_id = "schmidt"

    def search(self, query_params: dict | None = None) -> str:
        """Fetch the Schmidt Marine jobs page."""
        url = "https://jobs.schmidtmarine.org/jobs"
        response = self.fetch(url)
        return response.text

    def parse(self, raw_data: str) -> list[Job]:
        """
        Parse job listings from Schmidt Marine.

        Verified structure (2026-02):
          div[data-testid="job-list-item"]
            div[itemtype="https://schema.org/JobPosting"]
              [itemprop="title"] (job title)
              [itemprop="hiringOrganization"] (employer name)
              [itemprop="addressLocality"] (location)
              a[href="/companies/.../jobs/..."] (job URL)
        """
        soup = BeautifulSoup(raw_data, "lxml")
        jobs = []

        job_elements = soup.find_all("div", attrs={"data-testid": "job-list-item"})
        if not job_elements:
            logger.warning("Schmidt Marine: No job-list-item elements found")
            return jobs

        for element in job_elements:
            try:
                # Find schema.org JobPosting div
                schema_div = element.find("div", itemtype="https://schema.org/JobPosting")
                if not schema_div:
                    continue

                # Title from itemprop="title"
                title_elem = schema_div.find(attrs={"itemprop": "title"})
                if not title_elem:
                    continue
                title = title_elem.get_text(strip=True)

                # URL from job link
                job_link = schema_div.find("a", href=lambda x: x and "/jobs/" in x)
                if not job_link or not job_link.get("href"):
                    continue
                url = job_link["href"]
                if url.startswith("/"):
                    url = f"https://jobs.schmidtmarine.org{url}"

                # Job ID from URL (extract numeric ID)
                job_id_num = url.split("/jobs/")[-1].split("-")[0] if "/jobs/" in url else hash(url) % 1000000
                job_id = f"schmidt_{job_id_num}"

                # Employer from itemprop="hiringOrganization"
                employer_elem = schema_div.find(attrs={"itemprop": "hiringOrganization"})
                employer = employer_elem.get_text(strip=True) if employer_elem else "Schmidt Marine Technology Partners"

                # Location from itemprop="addressLocality"
                location_city = None
                location_state = None
                location_elem = schema_div.find(attrs={"itemprop": "addressLocality"})
                if location_elem:
                    location_text = location_elem.get_text(strip=True)
                    if location_text:
                        parts = [p.strip() for p in location_text.split(",")]
                        if len(parts) >= 1:
                            location_city = parts[0]
                        if len(parts) >= 2:
                            location_state = parts[1]

                # Description from itemprop="description"
                desc_elem = schema_div.find(attrs={"itemprop": "description"})
                description = desc_elem.get_text(strip=True) if desc_elem and desc_elem.get_text(strip=True) else f"{title} at {employer}"

                # Posted date from itemprop="datePosted"
                posted_elem = schema_div.find(attrs={"itemprop": "datePosted"})
                posted_text = posted_elem.get_text(strip=True) if posted_elem else ""

                job = Job(
                    job_id=job_id,
                    title=title,
                    employer=employer,
                    location_city=location_city,
                    location_state=location_state,
                    location_country="USA",
                    remote=False,
                    description=f"{description}. Posted: {posted_text}." if posted_text else description,
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
                logger.error("Error parsing Schmidt Marine job: %s", e)
                continue

        logger.info("Parsed %d jobs from Schmidt Marine", len(jobs))
        return jobs
