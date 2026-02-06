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

    def search(self, query_params: dict | None = None) -> list[str]:
        """
        Fetch Science Careers job listings pages with pagination.

        Returns list of HTML strings (one per page).
        """
        url = "https://jobs.sciencecareers.org/jobs/"
        # Pagination: Next link is in li.paginator__item > a (text="Next")
        return self.fetch_paginated(url, next_link_selector="li.paginator__item > a", max_pages=10)

    def parse(self, raw_data: list[str]) -> list[Job]:
        """
        Parse Science Careers HTML into Job objects (multi-page).

        Verified structure (2026-02):
          li.lister__item (job container, has id="item-{job_id}")
            div.lister__details
              h3.lister__header > a.js-clickable-area-link (href="/job/{id}/{slug}")
              ul.lister__meta
                li.lister__meta-item--location (location text)
                li.lister__meta-item--salary (salary text)
                li.lister__meta-item--recruiter (employer name)
              p.lister__description (description snippet)
        """
        jobs = []
        pages = raw_data if isinstance(raw_data, list) else [raw_data]

        job_elements = []
        for page_html in pages:
            soup = BeautifulSoup(page_html, "lxml")
            job_elements.extend(soup.find_all("li", class_="lister__item"))

        if not job_elements:
            logger.warning("Science Careers: No li.lister__item elements found")
            return jobs

        for element in job_elements:
            try:
                # Title + URL from h3.lister__header > a
                header = element.find("h3", class_="lister__header")
                if not header:
                    continue
                link = header.find("a", class_="js-clickable-area-link")
                if not link or not link.get("href"):
                    continue

                title = link.get_text(strip=True)
                url = link["href"].strip()
                if not url.startswith("http"):
                    url = f"https://jobs.sciencecareers.org{url}"

                # Job ID from element id attribute (e.g., "item-677025")
                element_id = element.get("id", "")
                if element_id.startswith("item-"):
                    source_id = element_id.replace("item-", "")
                else:
                    # Fallback: extract from URL
                    source_id = url.split("/")[-2] if "/" in url else str(hash(url) % 1000000)
                job_id = f"science_careers_{source_id}"

                # Employer, location, salary from ul.lister__meta
                employer = "Unknown Employer"
                location_text = None
                salary_range = None

                meta_list = element.find("ul", class_="lister__meta")
                if meta_list:
                    for meta_item in meta_list.find_all("li", class_="lister__meta-item"):
                        if "lister__meta-item--recruiter" in meta_item.get("class", []):
                            employer = meta_item.get_text(strip=True)
                        elif "lister__meta-item--location" in meta_item.get("class", []):
                            location_text = meta_item.get_text(strip=True)
                        elif "lister__meta-item--salary" in meta_item.get("class", []):
                            salary_range = meta_item.get_text(strip=True)

                # Parse location into city/state/country
                location_city, location_state, location_country, remote = self._parse_location(location_text)

                # Description from p.lister__description
                desc_elem = element.find("p", class_="lister__description")
                description = (
                    desc_elem.get_text(strip=True)
                    if desc_elem
                    else f"{title} at {employer}"
                )

                # Job type - default to full-time
                job_type = "full-time"

                jobs.append(
                    Job(
                        job_id=job_id,
                        title=title,
                        employer=employer,
                        location_city=location_city,
                        location_state=location_state,
                        location_country=location_country,
                        remote=remote,
                        description=description,
                        salary_range=salary_range,
                        job_type=job_type,
                        posted_date=None,
                        application_deadline=None,
                        url=url,
                        source=self.scraper_id,
                    )
                )

            except Exception as e:
                logger.error("Error parsing Science Careers job: %s", e)
                continue

        logger.info("Parsed %d jobs from Science Careers", len(jobs))
        return jobs

    def _parse_location(self, location: str | None) -> tuple[str | None, str | None, str, bool]:
        """Parse location string into city, state, country, and remote flag."""
        if not location:
            return None, None, "USA", False

        location_lower = location.lower()
        remote = "remote" in location_lower or "virtual" in location_lower

        # Remove remote indicator
        location = location.replace("(Remote)", "").replace("Remote", "").strip()

        # Split by comma and parse
        parts = [p.strip() for p in location.split(",")]
        if len(parts) == 0:
            return None, None, "USA", remote

        city = parts[0] if parts[0] else None

        # Check if last part looks like a country (has parentheses or is capitalized)
        country = "USA"
        state = None

        if len(parts) >= 2:
            last_part = parts[-1].strip()
            # If it's in parentheses like "(US)", it's a country code
            if last_part.startswith("(") and last_part.endswith(")"):
                country = last_part.strip("()")
                # If there are 3+ parts, middle is state/province
                if len(parts) >= 3:
                    state = parts[-2].strip()
            # If it looks like a country code (2-3 uppercase letters)
            elif len(last_part) <= 3 and last_part.isupper():
                country = last_part
                if len(parts) >= 3:
                    state = parts[-2].strip()
            else:
                # Assume it's a US state if 2-letter code or state name
                state = last_part

        return city, state, country, remote

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
