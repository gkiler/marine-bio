"""
EcoJobs scraper - ecojobs.com

Scrapes: https://ecojobs.com/natural-resources-and-conservation-jobs/

EcoJobs uses WordPress with Content Views plugin (pt-cv-* classes).
Job listings are in static HTML with pt-cv-content-item divs.

Flow:
1. Fetch EcoJobs Natural Resources & Conservation category page
2. Parse job listings from HTML using BeautifulSoup
3. Extract job details and create Job objects
"""

import logging
from datetime import datetime

from bs4 import BeautifulSoup

from core.schemas import Job
from scrapers.base_scraper import BaseScraper
from scrapers.scraper_manager import register_scraper

logger = logging.getLogger(__name__)


@register_scraper
class EcoJobs(BaseScraper):
    """Scraper for EcoJobs environmental job board."""

    scraper_id = "ecojobs"

    def search(self, query_params: dict | None = None) -> str:
        """
        Fetch EcoJobs Natural Resources & Conservation category page.

        Returns HTML string of the job search results.
        """
        # Use the Natural Resources & Conservation category which includes marine jobs
        url = "https://ecojobs.com/natural-resources-and-conservation-jobs/"

        logger.info("Fetching EcoJobs Natural Resources jobs")
        response = self.fetch(url)
        return response.text

    def parse(self, raw_data: str) -> list[Job]:
        """
        Parse EcoJobs HTML into Job objects.

        EcoJobs uses Content Views plugin with pt-cv-content-item divs.
        Each job has title in h4.pt-cv-title and location in pt-cv-custom-fields.
        """
        soup = BeautifulSoup(raw_data, "lxml")
        jobs = []

        # EcoJobs uses Content Views plugin with pt-cv-content-item class
        job_cards = soup.find_all("div", class_="pt-cv-content-item")

        if not job_cards:
            logger.warning("No job cards found - page structure may have changed")
            return jobs

        for idx, card in enumerate(job_cards):
            try:
                # Extract title and URL from h4.pt-cv-title > a
                title_elem = card.find("h4", class_="pt-cv-title")
                if not title_elem:
                    continue

                link = title_elem.find("a", href=True)
                if not link:
                    continue

                title = link.get_text(strip=True)
                url = link["href"]

                # Extract unique ID from URL
                url_parts = url.rstrip("/").split("/")
                source_id = url_parts[-1] if url_parts else str(idx)
                job_id = f"ecojobs_{source_id}"

                # Extract location from custom fields
                location_elem = card.find(
                    "div", class_="pt-cv-ctf-_job_location"
                )
                location = location_elem.get_text(strip=True) if location_elem else None
                location_city, location_state, remote = self._parse_location(location)

                # Extract employer from custom fields (if present)
                employer_elem = card.find("div", class_="pt-cv-ctf-_company_name")
                employer = (
                    employer_elem.get_text(strip=True)
                    if employer_elem
                    else "See job posting"
                )

                # Extract description from content area
                desc_elem = card.find("div", class_="pt-cv-content")
                description = (
                    desc_elem.get_text(strip=True)
                    if desc_elem
                    else title
                )

                # Job type - infer from title/description
                job_type = "full-time"
                title_lower = title.lower()
                if "intern" in title_lower or "intern" in description.lower():
                    job_type = "internship"
                elif "volunteer" in title_lower or "volunteer" in description.lower():
                    job_type = "volunteer"
                elif "part-time" in title_lower or "part time" in title_lower:
                    job_type = "part-time"
                elif "seasonal" in title_lower or "seasonal" in description.lower():
                    job_type = "seasonal"

                # Posted date - try to extract from pt-cv-ctf-post_date or similar
                date_elem = card.find("div", class_=lambda x: x and "date" in x.lower() if x else False)
                posted_date = self._parse_date(
                    date_elem.get_text(strip=True) if date_elem else None
                )

                jobs.append(
                    Job(
                        job_id=job_id,
                        title=title,
                        employer=employer,
                        location_city=location_city,
                        location_state=location_state,
                        remote=remote,
                        description=description,
                        job_type=job_type,
                        posted_date=posted_date,
                        url=url,
                        source=self.scraper_id,
                    )
                )

            except Exception as e:
                logger.warning("Failed to parse EcoJobs card %d: %s", idx, e)
                continue

        logger.info("Parsed %d jobs from EcoJobs", len(jobs))
        return jobs

    def _parse_location(self, location: str | None) -> tuple[str | None, str | None, bool]:
        """Parse location string into city, state, and remote flag."""
        if not location:
            return None, None, False

        location_lower = location.lower()
        remote = "remote" in location_lower or "virtual" in location_lower

        # Remove remote indicator
        location = location.replace("(Remote)", "").replace("Remote", "").strip()

        parts = [p.strip() for p in location.split(",")]
        city = parts[0] if parts else None
        state = parts[1] if len(parts) > 1 else None

        return city, state, remote

    def _normalize_job_type(self, job_type: str) -> str:
        """Normalize job type to standard values."""
        job_type_lower = job_type.lower()

        if "full" in job_type_lower or "permanent" in job_type_lower:
            return "full-time"
        elif "part" in job_type_lower:
            return "part-time"
        elif "intern" in job_type_lower:
            return "internship"
        elif "volunteer" in job_type_lower:
            return "volunteer"
        elif "seasonal" in job_type_lower or "temporary" in job_type_lower:
            return "seasonal"
        else:
            return job_type_lower

    def _parse_date(self, date_str: str | None) -> datetime | None:
        """Parse date string into datetime object."""
        if not date_str:
            return None

        try:
            # Handle relative dates
            if "ago" in date_str.lower():
                return datetime.now()

            # Try common formats
            for fmt in ["%Y-%m-%d", "%b %d, %Y", "%B %d, %Y", "%d/%m/%Y", "%m/%d/%Y"]:
                try:
                    return datetime.strptime(date_str, fmt)
                except ValueError:
                    continue

            return None
        except Exception:
            return None
