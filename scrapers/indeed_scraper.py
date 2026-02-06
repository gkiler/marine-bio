"""
Indeed scraper - indeed.com (search: "marine biology")

NOTE: This site requires JavaScript rendering. Job listings are dynamically loaded
and not present in the static HTML. Indeed also implements aggressive bot detection.
Selectors below are best-guess patterns and will not work without a JavaScript-enabled
browser/scraper (e.g., Playwright, Selenium) and may require proxy/anti-detection measures.

Flow:
1. Fetch Indeed job search page with marine biology keywords
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
class Indeed(BaseScraper):
    """Scraper for Indeed job board with marine biology filters."""

    scraper_id = "indeed"

    def search(self, query_params: dict | None = None) -> str:
        """
        Fetch Indeed job listings page for marine biology.

        Returns HTML string of the job search results.
        """
        url = "https://www.indeed.com/jobs"
        params = {
            "q": "marine biology oceanography aquatic",
            "l": "",  # location (empty for all US)
            "sort": "date",
        }

        if query_params:
            params.update(query_params)

        logger.info("Fetching Indeed jobs with params: %s", params)
        response = self.fetch(url, params=params)
        return response.text

    def parse(self, raw_data: str) -> list[Job]:
        """
        Parse Indeed HTML into Job objects.

        Handles missing fields gracefully by setting to None.
        """
        soup = BeautifulSoup(raw_data, "lxml")
        jobs = []

        # Indeed uses various selectors for job cards
        job_cards = (
            soup.find_all("div", class_="job_seen_beacon")
            or soup.find_all("div", class_="jobsearch-SerpJobCard")
            or soup.find_all("a", class_="result")
            or soup.find_all("div", attrs={"data-jk": True})
        )

        if not job_cards:
            logger.warning("No job cards found - page structure may have changed")
            return jobs

        for card in job_cards:
            try:
                # Extract job ID from data attribute
                job_key = card.get("data-jk") or card.get("id", "")
                if not job_key:
                    # Try to find in nested elements
                    link = card.find("a", attrs={"data-jk": True})
                    if link:
                        job_key = link.get("data-jk", "")

                if not job_key:
                    continue

                job_id = f"indeed_{job_key}"
                url = f"https://www.indeed.com/viewjob?jk={job_key}"

                # Title
                title_elem = (
                    card.find("h2", class_="jobTitle")
                    or card.find("a", class_="jcs-JobTitle")
                    or card.find("span", attrs={"title": True})
                )
                if title_elem:
                    title_link = title_elem.find("span", attrs={"title": True})
                    title = (
                        title_link.get("title", "")
                        if title_link
                        else title_elem.get_text(strip=True)
                    )
                else:
                    title = "Unknown Title"

                # Employer
                employer_elem = (
                    card.find("span", class_="companyName")
                    or card.find("span", class_="company")
                    or card.find("div", class_="company")
                )
                employer = (
                    employer_elem.get_text(strip=True)
                    if employer_elem
                    else "Unknown Employer"
                )

                # Location
                location_elem = (
                    card.find("div", class_="companyLocation")
                    or card.find("span", class_="location")
                    or card.find("div", class_="location")
                )
                location = (
                    location_elem.get_text(strip=True) if location_elem else None
                )
                location_city, location_state, remote = self._parse_location(location)

                # Description/snippet
                desc_elem = (
                    card.find("div", class_="job-snippet")
                    or card.find("div", class_="summary")
                    or card.find("ul")
                )
                description = (
                    desc_elem.get_text(strip=True)
                    if desc_elem
                    else "No description available"
                )

                # Salary
                salary_elem = (
                    card.find("div", class_="salary-snippet")
                    or card.find("span", class_="salaryText")
                )
                salary_range = (
                    salary_elem.get_text(strip=True) if salary_elem else None
                )

                # Job type - Indeed shows this in metadata
                metadata = card.find_all("div", class_="metadata")
                job_type = "full-time"  # Default
                for meta in metadata:
                    text = meta.get_text(strip=True).lower()
                    if any(t in text for t in ["part-time", "full-time", "contract", "internship"]):
                        job_type = self._normalize_job_type(text)
                        break

                # Posted date - Indeed shows relative dates
                date_elem = card.find("span", class_="date")
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

        logger.info("Parsed %d jobs from Indeed", len(jobs))
        return jobs

    def _parse_location(self, location: str | None) -> tuple[str | None, str | None, bool]:
        """Parse location string into city, state, and remote flag."""
        if not location:
            return None, None, False

        location_lower = location.lower()
        remote = "remote" in location_lower or "work from home" in location_lower

        # Remove remote indicator
        location = (
            location.replace("(Remote)", "")
            .replace("Remote", "")
            .replace("Work from Home", "")
            .strip()
        )

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
        elif "contract" in job_type_lower or "temporary" in job_type_lower:
            return "seasonal"
        else:
            return job_type_lower

    def _parse_date(self, date_str: str | None) -> datetime | None:
        """Parse date string into datetime object."""
        if not date_str:
            return None

        try:
            # Handle relative dates (Indeed uses these frequently)
            if "just posted" in date_str.lower() or "today" in date_str.lower():
                return datetime.now()

            if "ago" in date_str.lower():
                # Approximate for "X days ago"
                return datetime.now()

            # Try common formats
            for fmt in ["%Y-%m-%d", "%b %d, %Y", "%B %d, %Y", "%m/%d/%Y"]:
                try:
                    return datetime.strptime(date_str, fmt)
                except ValueError:
                    continue

            return None
        except Exception:
            return None
