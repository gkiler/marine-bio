"""
EnvironmentalCareer scraper - environmentalcareer.com

Flow:
1. Fetch EnvironmentalCareer job search page
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
class EnvironmentalCareer(BaseScraper):
    """Scraper for Environmental Career job board."""

    scraper_id = "envcareer"

    def search(self, query_params: dict | None = None) -> str:
        """
        Fetch EnvironmentalCareer job listings page.

        Returns HTML string of the job search results. No pagination on this site.
        """
        url = "https://environmentalcareer.com/jobs/"
        logger.info("Fetching EnvironmentalCareer jobs")
        response = self.fetch(url)
        return response.text

    def parse(self, raw_data: str) -> list[Job]:
        """
        Parse EnvironmentalCareer HTML into Job objects.

        Verified structure (2026-02):
          article.listing-item
            div.listing-item__title > a.link (href="/job/{id}/{slug}", title text)
            div.listing-item__info
              span.listing-item__info--item-company (employer)
              span.listing-item__info--item-location (location)
            span.listing-item__employment-type (job type)
            div.listing-item__date (posted date)
            div.listing-item__desc (description snippet)
        """
        soup = BeautifulSoup(raw_data, "lxml")
        jobs = []

        job_elements = soup.find_all("article", class_="listing-item")
        if not job_elements:
            logger.warning("EnvironmentalCareer: No article.listing-item elements found")
            return jobs

        for element in job_elements:
            try:
                # Title + URL from div.listing-item__title > a
                title_div = element.find("div", class_="listing-item__title")
                if not title_div:
                    continue
                link = title_div.find("a", class_="link")
                if not link or not link.get("href"):
                    continue

                title = link.get_text(strip=True)
                url = link["href"]
                if not url.startswith("http"):
                    url = f"https://environmentalcareer.com{url}"

                # Job ID from URL (e.g., "/job/81723/title/" -> "81723")
                url_parts = url.split("/")
                source_id = url_parts[4] if len(url_parts) > 4 else str(hash(url) % 1000000)
                job_id = f"envcareer_{source_id}"

                # Employer and location from div.listing-item__info
                employer = "Unknown Employer"
                location_text = None
                info_div = element.find("div", class_="listing-item__info")
                if info_div:
                    company_span = info_div.find("span", class_="listing-item__info--item-company")
                    if company_span:
                        employer = company_span.get_text(strip=True)
                    location_span = info_div.find("span", class_="listing-item__info--item-location")
                    if location_span:
                        location_text = location_span.get_text(strip=True)

                # Parse location
                location_city, location_state, remote = self._parse_location(location_text)

                # Job type from span.listing-item__employment-type
                job_type_elem = element.find("span", class_="listing-item__employment-type")
                job_type = (
                    self._normalize_job_type(job_type_elem.get_text(strip=True))
                    if job_type_elem
                    else "full-time"
                )

                # Posted date from div.listing-item__date
                date_elem = element.find("div", class_="listing-item__date")
                posted_date = self._parse_date(
                    date_elem.get_text(strip=True) if date_elem else None
                )

                # Description from div.listing-item__desc
                desc_elem = element.find("div", class_="listing-item__desc")
                description = (
                    desc_elem.get_text(strip=True)
                    if desc_elem
                    else f"{title} at {employer}"
                )

                jobs.append(
                    Job(
                        job_id=job_id,
                        title=title,
                        employer=employer,
                        location_city=location_city,
                        location_state=location_state,
                        location_country="USA",
                        remote=remote,
                        description=description,
                        salary_range=None,
                        job_type=job_type,
                        posted_date=posted_date,
                        application_deadline=None,
                        url=url,
                        source=self.scraper_id,
                    )
                )

            except Exception as e:
                logger.error("Error parsing EnvironmentalCareer job: %s", e)
                continue

        logger.info("Parsed %d jobs from EnvironmentalCareer", len(jobs))
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
