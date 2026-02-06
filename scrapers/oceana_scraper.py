"""
Oceana employment opportunities scraper.

Scrapes https://oceana.org/employment-opportunities for marine conservation jobs.
Uses HTML parsing with BeautifulSoup4.
"""

import logging
from datetime import datetime

from bs4 import BeautifulSoup

from core.schemas import Job
from scrapers.base_scraper import BaseScraper
from scrapers.scraper_manager import register_scraper

logger = logging.getLogger(__name__)


@register_scraper
class OceanaScraper(BaseScraper):
    """Scraper for Oceana job listings."""

    scraper_id = "oceana"

    def search(self, query_params: dict | None = None) -> str:
        """
        Fetch the Oceana employment opportunities page.

        Returns raw HTML.
        """
        url = "https://oceana.org/employment-opportunities"
        response = self.fetch(url)
        return response.text

    def parse(self, raw_data: str) -> list[Job]:
        """
        Parse Oceana HTML to extract job listings.

        Verified structure (2026-02):
          div.php-to-be-replaced-with-shortcode.wpv-block-loop-item
            h2.tb-heading (location)
            p.tb-heading > a (title + href)
        """
        soup = BeautifulSoup(raw_data, "lxml")
        jobs = []

        # Find job items (server-rendered from PHP shortcode)
        job_cards = soup.find_all("div", class_="wpv-block-loop-item")
        if not job_cards:
            logger.warning("Oceana: No div.wpv-block-loop-item elements found")
            return jobs

        for idx, card in enumerate(job_cards):
            try:
                # Location from h2.tb-heading
                location_h2 = card.find("h2", class_="tb-heading")
                location_text = location_h2.get_text(strip=True) if location_h2 else None

                city, state = None, None
                remote = False
                if location_text:
                    remote = "remote" in location_text.lower()
                    parts = location_text.split(",")
                    if len(parts) >= 1:
                        city = parts[0].strip()
                    if len(parts) >= 2:
                        state = parts[1].strip()

                # Title + URL from p.tb-heading > a
                title_p = card.find("p", class_="tb-heading")
                if not title_p:
                    continue
                link = title_p.find("a", href=True)
                if not link:
                    continue

                title = link.get_text(strip=True)
                url = link["href"]
                if not url.startswith("http"):
                    url = f"https://oceana.org{url}"

                job = Job(
                    job_id=f"{self.scraper_id}_{hash(url) % 1000000}",
                    title=title,
                    employer="Oceana",
                    location_city=city,
                    location_state=state,
                    location_country="USA",
                    remote=remote,
                    description=f"{title} at Oceana",
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
                logger.warning("Failed to parse Oceana job card %d: %s", idx, e)
                continue

        logger.info("Oceana scraper found %d jobs", len(jobs))
        return jobs
