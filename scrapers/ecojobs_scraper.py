"""
EcoJobs scraper - ecojobs.com

NOTE: This site requires JavaScript rendering. Job listings are dynamically loaded
and not present in the static HTML. Selectors below are best-guess patterns and will
not work without a JavaScript-enabled browser/scraper (e.g., Playwright, Selenium).

Flow:
1. Fetch EcoJobs search page
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
        Fetch EcoJobs job listings page.

        Returns HTML string of the job search results.
        """
        url = "https://www.ecojobs.com/search"
        params = {
            "q": "marine oceanography aquatic conservation",
            "l": "",  # location (empty for all)
        }

        if query_params:
            params.update(query_params)

        logger.info("Fetching EcoJobs with params: %s", params)
        response = self.fetch(url, params=params)
        return response.text

    def parse(self, raw_data: str) -> list[Job]:
        """
        Parse EcoJobs HTML into Job objects.

        Handles missing fields gracefully by setting to None.
        """
        soup = BeautifulSoup(raw_data, "lxml")
        jobs = []

        # EcoJobs typically uses div or article tags for job listings
        job_cards = (
            soup.find_all("div", class_="job-listing")
            or soup.find_all("article", class_="job")
            or soup.find_all("div", class_="job-card")
        )

        if not job_cards:
            logger.warning("No job cards found - page structure may have changed")
            return jobs

        for card in job_cards:
            try:
                # Extract job link
                job_link = card.find("a", class_="job-link") or card.find("a", href=True)
                if not job_link:
                    continue

                url = job_link.get("href", "")
                if not url.startswith("http"):
                    url = f"https://www.ecojobs.com{url}"

                # Extract unique ID from URL
                source_id = url.split("/")[-1] if "/" in url else url
                job_id = f"ecojobs_{source_id}"

                # Title
                title_elem = card.find("h2") or card.find("h3") or job_link
                title = title_elem.get_text(strip=True) if title_elem else "Unknown Title"

                # Employer
                employer_elem = card.find("span", class_="company") or card.find(
                    "div", class_="company"
                ) or card.find("p", class_="employer")
                employer = (
                    employer_elem.get_text(strip=True)
                    if employer_elem
                    else "Unknown Employer"
                )

                # Location
                location_elem = card.find("span", class_="location") or card.find(
                    "div", class_="location"
                )
                location = (
                    location_elem.get_text(strip=True) if location_elem else None
                )
                location_city, location_state, remote = self._parse_location(location)

                # Description
                desc_elem = card.find("div", class_="description") or card.find(
                    "p", class_="summary"
                ) or card.find("p")
                description = (
                    desc_elem.get_text(strip=True)
                    if desc_elem
                    else "No description available"
                )

                # Job type
                job_type_elem = card.find("span", class_="job-type") or card.find(
                    "span", class_="type"
                )
                job_type = (
                    self._normalize_job_type(job_type_elem.get_text(strip=True))
                    if job_type_elem
                    else "full-time"
                )

                # Posted date
                date_elem = card.find("time") or card.find("span", class_="date")
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
                logger.warning("Failed to parse job card: %s", e)
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
