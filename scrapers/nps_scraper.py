# NOTE: NPS does not host jobs directly. All NPS positions are posted on USAJOBS.gov.
# The work-with-us page links to https://www.usajobs.gov/Search?keyword='national park service'
# This scraper will return 0 jobs. Use the USAJOBS scraper instead.

"""
National Park Service careers scraper.

Scrapes https://www.nps.gov/aboutus/workwithus.htm for park service jobs.
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
class NpsScraper(BaseScraper):
    """Scraper for National Park Service job listings."""

    scraper_id = "nps"

    def search(self, query_params: dict | None = None) -> str:
        """
        Fetch the NPS work with us page.

        Returns raw HTML.
        """
        url = "https://www.nps.gov/aboutus/workwithus.htm"
        response = self.fetch(url)
        return response.text

    def parse(self, raw_data: str) -> list[Job]:
        """
        Parse NPS HTML to extract job listings.

        NPS often redirects to USAJOBS for permanent positions, but may have
        seasonal or volunteer opportunities listed directly. Handle missing fields gracefully.
        """
        soup = BeautifulSoup(raw_data, "lxml")
        jobs = []

        # Look for job listings
        job_cards = soup.find_all("div", class_=lambda x: x and "job" in x.lower()) or \
                    soup.find_all("li", class_=lambda x: x and "job" in x.lower()) or \
                    soup.find_all("article") or \
                    soup.find_all("div", class_="position")

        for idx, card in enumerate(job_cards):
            try:
                # Extract title
                title_elem = card.find("h2") or card.find("h3") or card.find("h4") or \
                             card.find("a")
                if not title_elem:
                    continue
                title = title_elem.get_text(strip=True)

                # Skip if title suggests external link
                if "usajobs" in title.lower() or "apply at" in title.lower():
                    continue

                # Extract URL
                link_elem = card.find("a", href=True)
                if link_elem:
                    url = link_elem["href"]
                    if not url.startswith("http"):
                        url = f"https://www.nps.gov{url}"
                else:
                    url = "https://www.nps.gov/aboutus/workwithus.htm"

                # Extract location
                location_elem = card.find(class_=lambda x: x and "location" in x.lower()) or \
                               card.find("span", string=lambda s: s and ("location" in s.lower() if s else False))
                location_text = location_elem.get_text(strip=True) if location_elem else None

                city, state = None, None
                remote = False
                if location_text:
                    remote = "remote" in location_text.lower()
                    parts = location_text.split(",")
                    if len(parts) >= 1:
                        city = parts[0].strip()
                    if len(parts) >= 2:
                        state = parts[1].strip()

                # Extract description
                desc_elem = card.find("p") or card.find(class_="description") or \
                           card.find(class_="summary")
                description = desc_elem.get_text(strip=True) if desc_elem else title

                # Extract job type
                type_elem = card.find(class_=lambda x: x and "type" in x.lower())
                job_type_text = type_elem.get_text(strip=True).lower() if type_elem else "seasonal"
                if "intern" in job_type_text:
                    job_type = "internship"
                elif "volunteer" in job_type_text:
                    job_type = "volunteer"
                elif "part" in job_type_text:
                    job_type = "part-time"
                elif "seasonal" in job_type_text:
                    job_type = "seasonal"
                elif "full" in job_type_text:
                    job_type = "full-time"
                else:
                    job_type = "seasonal"  # NPS is often seasonal

                job = Job(
                    job_id=f"{self.scraper_id}_{idx}",
                    title=title,
                    employer="National Park Service",
                    location_city=city,
                    location_state=state,
                    location_country="USA",
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
                logger.warning("Failed to parse NPS job card %d: %s", idx, e)
                continue

        logger.info("NPS scraper found %d jobs", len(jobs))
        return jobs
