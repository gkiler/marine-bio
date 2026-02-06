"""
Science Careers scraper - jobs.sciencecareers.org (AAAS)

Flow:
1. Fetch Science Careers job search page
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
class ScienceCareers(BaseScraper):
    """Scraper for AAAS Science Careers job board."""

    scraper_id = "science_careers"

    def search(self, query_params: dict | None = None) -> str:
        """
        Fetch Science Careers job listings page.

        Returns HTML string of the job search results.
        """
        url = "https://jobs.sciencecareers.org/jobs"
        params = {
            "keywords": "marine biology oceanography aquatic ecology",
            "page": "1",
        }

        if query_params:
            params.update(query_params)

        logger.info("Fetching Science Careers jobs with params: %s", params)
        response = self.fetch(url, params=params)
        return response.text

    def parse(self, raw_data: str) -> list[Job]:
        """
        Parse Science Careers HTML into Job objects.

        Handles missing fields gracefully by setting to None.
        """
        soup = BeautifulSoup(raw_data, "lxml")
        jobs = []

        # Science Careers uses li or div tags for job listings
        job_cards = (
            soup.find_all("li", class_="job")
            or soup.find_all("div", class_="job-result")
            or soup.find_all("article", class_="job")
        )

        if not job_cards:
            logger.warning("No job cards found - page structure may have changed")
            return jobs

        for card in job_cards:
            try:
                # Extract job link
                job_link = card.find("a", class_="job-title") or card.find("a", href=True)
                if not job_link:
                    continue

                url = job_link.get("href", "")
                if not url.startswith("http"):
                    url = f"https://jobs.sciencecareers.org{url}"

                # Extract unique ID from URL
                source_id = url.split("/")[-1] if "/" in url else url
                job_id = f"science_careers_{source_id}"

                # Title
                title = job_link.get_text(strip=True) or "Unknown Title"

                # Employer
                employer_elem = card.find("span", class_="company") or card.find(
                    "div", class_="employer"
                ) or card.find("a", class_="employer")
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
                    "p", class_="snippet"
                )
                description = (
                    desc_elem.get_text(strip=True)
                    if desc_elem
                    else "No description available"
                )

                # Job type
                job_type_elem = card.find("span", class_="job-type")
                job_type = (
                    job_type_elem.get_text(strip=True).lower()
                    if job_type_elem
                    else "full-time"
                )

                # Posted date
                date_elem = card.find("time") or card.find("span", class_="date")
                posted_date = self._parse_date(
                    date_elem.get_text(strip=True) if date_elem else None
                )

                # Salary
                salary_elem = card.find("span", class_="salary")
                salary_range = (
                    salary_elem.get_text(strip=True) if salary_elem else None
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
                        salary_range=salary_range,
                        job_type=job_type,
                        posted_date=posted_date,
                        url=url,
                        source=self.scraper_id,
                    )
                )

            except Exception as e:
                logger.warning("Failed to parse job card: %s", e)
                continue

        logger.info("Parsed %d jobs from Science Careers", len(jobs))
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
