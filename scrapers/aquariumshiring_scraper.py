"""
AquariumsHiring.com job scraper.

Scrapes: https://www.aquariumshiring.com
"""

import logging
from datetime import datetime

from bs4 import BeautifulSoup

from core.schemas import Job
from scrapers.base_scraper import BaseScraper
from scrapers.scraper_manager import register_scraper

logger = logging.getLogger(__name__)


@register_scraper
class AquariumsHiringScraper(BaseScraper):
    """
    Scraper for AquariumsHiring.com job board.

    Flow:
    1. Fetch job listings page
    2. Parse job postings for aquarium positions
    3. Extract metadata and links
    """

    scraper_id = "aquariumshiring"

    def search(self, query_params: dict | None = None) -> list[str]:
        """Fetch all pages of AquariumsHiring.com jobs."""
        url = "https://www.aquariumshiring.com"
        # Pagination: <a class="pagination-next" href="/2">Next page</a>
        return self.fetch_paginated(url, next_link_selector="a.pagination-next", max_pages=10)

    def parse(self, raw_data: list[str]) -> list[Job]:
        """
        Parse aquarium job listings from HTML (multi-page).

        Verified structure (2026-02):
          div.card > a[href] (job URL)
            div.card-content > div.media
              div.media-content
                h2.title.is-4 (job title)
                h3.subtitle.is-6 (employer name, location separated by <br/>)
        """
        jobs = []
        pages = raw_data if isinstance(raw_data, list) else [raw_data]

        job_cards = []
        for page_html in pages:
            soup = BeautifulSoup(page_html, "lxml")
            job_cards.extend(soup.find_all("div", class_="card"))

        if not job_cards:
            logger.warning("AquariumsHiring: No div.card elements found")
            return jobs

        logger.info("AquariumsHiring: Found %d job cards", len(job_cards))

        for card in job_cards:
            try:
                # Get the link (wraps entire card)
                link = card.find("a", href=True)
                if not link:
                    continue

                url = link["href"]
                if not url.startswith("http"):
                    url = f"https://www.aquariumshiring.com{url}"

                # Extract job ID from URL (e.g., /jobs/veterinary-technician-atlanta-2)
                job_slug = url.split("/")[-1] if "/" in url else hash(url) % 1000000
                job_id = f"aquariumshiring_{job_slug}"

                # Title from h2.title.is-4
                title_h2 = card.find("h2", class_="title")
                if not title_h2:
                    continue
                title = title_h2.get_text(strip=True)

                # Employer + location from h3.subtitle.is-6 (separated by <br/>)
                subtitle_h3 = card.find("h3", class_="subtitle")
                if not subtitle_h3:
                    continue

                # Split by <br/> to get employer and location
                subtitle_parts = subtitle_h3.decode_contents().split("<br/>")
                employer = BeautifulSoup(subtitle_parts[0], "lxml").get_text(strip=True) if subtitle_parts else "Unknown Aquarium"
                location_text = BeautifulSoup(subtitle_parts[1], "lxml").get_text(strip=True) if len(subtitle_parts) > 1 else ""

                # Parse location (format: "Atlanta, United States")
                location_city = None
                location_state = None
                location_country = "USA"
                if location_text:
                    parts = [p.strip() for p in location_text.split(",")]
                    if len(parts) >= 2:
                        location_city = parts[0]
                        # Could be state or country
                        second_part = parts[1]
                        if second_part in ["United States", "USA"]:
                            location_country = "USA"
                        else:
                            location_state = second_part
                    elif len(parts) == 1:
                        location_city = parts[0]

                # Determine job type from title
                job_type = "full-time"
                title_lower = title.lower()
                if "intern" in title_lower:
                    job_type = "internship"
                elif "volunteer" in title_lower:
                    job_type = "volunteer"
                elif "part-time" in title_lower or "part time" in title_lower:
                    job_type = "part-time"
                elif "seasonal" in title_lower:
                    job_type = "seasonal"

                job = Job(
                    job_id=job_id,
                    title=title,
                    employer=employer,
                    location_city=location_city,
                    location_state=location_state,
                    location_country=location_country,
                    remote=False,
                    description=f"{title} at {employer}.",
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
                logger.error("Error parsing AquariumsHiring job card: %s", e)
                continue

        logger.info("AquariumsHiring scraper parsed %d jobs", len(jobs))
        return jobs
