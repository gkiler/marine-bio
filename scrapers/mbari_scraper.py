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
        """Fetch MBARI job openings page HTML."""
        url = "https://www.mbari.org/about/careers/job-openings/"
        response = self.fetch(url)
        return response.text

    def parse(self, raw_data: str) -> list[Job]:
        """
        Parse MBARI job listings from HTML.

        Verified structure (2026-02):
          article.list-item--job-opening > a.list-item__link (wraps entire job)
            h1.list-item__title (job title)
            div.list-item__excerpt > p (description snippet)

        URL pattern: https://www.mbari.org/job-opening/{slug}/
        """
        soup = BeautifulSoup(raw_data, "lxml")
        jobs = []

        # Find job articles
        job_articles = soup.find_all("article", class_="list-item--job-opening")
        if not job_articles:
            logger.warning("MBARI: No article.list-item--job-opening elements found")
            return jobs

        logger.info("MBARI: Found %d job articles", len(job_articles))

        for article in job_articles:
            try:
                # Get the link (wraps the entire article content)
                link = article.find("a", class_="list-item__link")
                if not link or not link.get("href"):
                    continue

                url = link["href"]

                # Extract job ID from URL (e.g., /job-opening/ocean-observatory-trainee/)
                job_slug = url.rstrip("/").split("/")[-1] if "/" in url else hash(url) % 1000000
                job_id = f"mbari_{job_slug}"

                # Title from h1.list-item__title
                title_h1 = article.find("h1", class_="list-item__title")
                if not title_h1:
                    continue
                title = title_h1.get_text(strip=True)

                # Description excerpt from div.list-item__excerpt > p
                excerpt_div = article.find("div", class_="list-item__excerpt")
                description = title
                if excerpt_div:
                    excerpt_p = excerpt_div.find("p")
                    if excerpt_p:
                        description = excerpt_p.get_text(strip=True)[:200]

                # Determine job type from title
                job_type = "full-time"
                title_lower = title.lower()
                if "intern" in title_lower:
                    job_type = "internship"
                elif "trainee" in title_lower or "apprentice" in title_lower:
                    job_type = "internship"
                elif "fellow" in title_lower or "postdoc" in title_lower:
                    job_type = "full-time"
                elif "volunteer" in title_lower:
                    job_type = "volunteer"
                elif "seasonal" in title_lower or "summer" in title_lower:
                    job_type = "seasonal"

                job = Job(
                    job_id=job_id,
                    title=title,
                    employer="Monterey Bay Aquarium Research Institute",
                    location_city="Moss Landing",
                    location_state="CA",
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
                logger.error("Error parsing MBARI job: %s", e)
                continue

        logger.info("MBARI scraper parsed %d jobs", len(jobs))
        return jobs
