"""
Climatebase marine/ocean jobs scraper.

Uses Playwright to render the React SPA and extract job cards.

Verified DOM structure (2026-02-12, Playwright render):
  a.job__card (each card is an <a> with full href)
    div.Card_Information__HkDL9
      h2 (title)
      ul > li elements (employer, location, remote/hybrid, job type)
      p.Card_Details__NXC2i (description snippet)
"""

import logging
from urllib.parse import urlencode

from bs4 import BeautifulSoup

from core.schemas import Job
from scrapers.playwright_scraper import PlaywrightScraper
from scrapers.scraper_manager import register_scraper

logger = logging.getLogger(__name__)


@register_scraper
class ClimatebaseScraper(PlaywrightScraper):
    """Scraper for Climatebase marine/ocean jobs (React SPA)."""

    scraper_id = "climatebase"

    def search(self, query_params: dict | None = None) -> str:
        """
        Render Climatebase search page with marine+ocean filter.

        Returns rendered HTML string with job cards loaded.
        """
        params = urlencode({"l": "", "q": "marine ocean", "p": "1"})
        url = f"https://climatebase.org/jobs?{params}"
        return self.fetch_rendered(url, wait_selector="a.job__card", timeout=45000)

    def parse(self, raw_data: str) -> list[Job]:
        """
        Parse job cards from rendered Climatebase HTML.

        Each card is an <a class="job__card"> containing:
          - h2: title
          - ul > li[0]: employer (class includes 'fntWMF')
          - ul > li[1]: location
          - ul > li[2]: remote/hybrid/in-person
          - ul > li[3]: job type (Full time role, etc.)
          - p.Card_Details__NXC2i: description snippet
          - href: full URL to job posting
        """
        soup = BeautifulSoup(raw_data, "lxml")
        cards = soup.find_all("a", class_="job__card")

        if not cards:
            logger.warning("Climatebase: no a.job__card elements found")
            return []

        jobs: list[Job] = []
        for card in cards:
            try:
                href = card.get("href", "")
                if not href:
                    continue

                # Title from h2
                h2 = card.find("h2")
                title = h2.get_text(strip=True) if h2 else ""
                if not title:
                    continue

                # Metadata from ul > li elements
                info_ul = card.find("ul")
                li_items = info_ul.find_all("li") if info_ul else []

                employer = li_items[0].get_text(strip=True) if len(li_items) > 0 else "Unknown"
                location_raw = li_items[1].get_text(strip=True) if len(li_items) > 1 else ""
                work_mode = li_items[2].get_text(strip=True) if len(li_items) > 2 else ""
                job_type_raw = li_items[3].get_text(strip=True) if len(li_items) > 3 else "full-time"

                # Parse location
                location_city = None
                location_state = None
                location_country = "USA"
                remote = "remote" in work_mode.lower()

                if location_raw:
                    parts = [p.strip() for p in location_raw.split(",")]
                    if len(parts) >= 2:
                        location_city = parts[0]
                        location_state = parts[1]
                    if len(parts) >= 3:
                        location_country = parts[-1]

                # Normalize job type
                type_map = {
                    "full time role": "full-time",
                    "part time role": "part-time",
                    "internship": "internship",
                    "contract role": "seasonal",
                    "volunteer role": "volunteer",
                }
                job_type = type_map.get(job_type_raw.lower(), "full-time")

                # Description
                desc_el = card.find("p", class_=lambda c: c and "Card_Details" in c)
                description = desc_el.get_text(strip=True) if desc_el else f"{title} at {employer}"

                # Extract job ID from URL
                # e.g. /job/67961909/postdoctoral-research-associate...
                job_id_num = href.split("/job/")[-1].split("/")[0] if "/job/" in href else str(hash(href) % 1000000)

                jobs.append(Job(
                    job_id=f"climatebase_{job_id_num}",
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
                    url=href,
                    source=self.scraper_id,
                ))

            except Exception as e:
                logger.error("Error parsing Climatebase job card: %s", e)
                continue

        logger.info("Parsed %d jobs from Climatebase", len(jobs))
        return jobs
