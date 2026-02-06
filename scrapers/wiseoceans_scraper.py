"""
Wise Oceans marine conservation jobs scraper (HTML).

Scrapes marine conservation job listings from Wise Oceans.
"""

import logging

from bs4 import BeautifulSoup

from core.schemas import Job
from scrapers.base_scraper import BaseScraper
from scrapers.scraper_manager import register_scraper

logger = logging.getLogger(__name__)


@register_scraper
class WiseOceansScraper(BaseScraper):
    """Scraper for Wise Oceans marine conservation jobs."""

    scraper_id = "wiseoceans"

    def search(self, query_params: dict | None = None) -> list[str]:
        """Fetch all pages of Wise Oceans jobs (paginated)."""
        url = "https://wiseoceans.com/jobs"
        # Pagination uses <a rel="next">
        return self.fetch_paginated(url, next_link_selector="a[rel='next']", max_pages=10)

    def parse(self, raw_data: list[str]) -> list[Job]:
        """
        Parse marine conservation job listings from Wise Oceans.

        Verified structure (2026-02):
          article.job-block
            h5 > a (title + URL)
            span.company (employer name)
            span.location (location with icon)
            div.uk-text-small (job type, posted date)
        """
        jobs = []
        pages = raw_data if isinstance(raw_data, list) else [raw_data]

        job_elements = []
        for page_html in pages:
            soup = BeautifulSoup(page_html, "lxml")
            job_elements.extend(soup.find_all("article", class_="job-block"))

        if not job_elements:
            logger.warning("Wise Oceans: No article.job-block elements found")
            return jobs

        for element in job_elements:
            try:
                # Title + URL from h5 > a
                title_h5 = element.find("h5")
                if not title_h5:
                    continue
                link = title_h5.find("a")
                if not link or not link.get("href"):
                    continue

                title = link.get_text(strip=True)
                url = link["href"]
                if not url.startswith("http"):
                    url = f"https://wiseoceans.com{url}"

                # Job ID from URL
                job_id_slug = url.rstrip("/").split("/")[-1]
                job_id = f"wiseoceans_{job_id_slug}"

                # Employer from span.company
                employer_elem = element.find("span", class_="company")
                employer = employer_elem.get_text(strip=True) if employer_elem else "Unknown Organization"

                # Location from span.location (has icon, extract text)
                location_city = None
                location_state = None
                location_country = "Unknown"
                remote = False
                location_elem = element.find("span", class_="location")
                if location_elem:
                    location_text = location_elem.get_text(strip=True)
                    if "remote" in location_text.lower():
                        remote = True
                    # Parse "City, Country" format
                    parts = [p.strip() for p in location_text.split(",")]
                    if len(parts) >= 1:
                        location_city = parts[0]
                    if len(parts) >= 2:
                        location_country = parts[-1]
                        if len(parts) == 3:
                            location_state = parts[1]

                # Job type from badges or text (volunteer/internship/full-time)
                job_type = "full-time"
                badges = element.find_all("span", class_="job-badge")
                for badge in badges:
                    badge_text = badge.get_text(strip=True).lower()
                    if "volunteer" in badge_text:
                        job_type = "volunteer"
                    elif "intern" in badge_text:
                        job_type = "internship"
                    elif "part" in badge_text:
                        job_type = "part-time"

                # Description (there's no visible description in the listing, use title)
                description = f"{title} at {employer}"

                job = Job(
                    job_id=job_id,
                    title=title,
                    employer=employer,
                    location_city=location_city,
                    location_state=location_state,
                    location_country=location_country,
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
                logger.error("Error parsing Wise Oceans job: %s", e)
                continue

        logger.info("Parsed %d jobs from Wise Oceans", len(jobs))
        return jobs
