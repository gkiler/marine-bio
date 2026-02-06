"""
Florida government marine careers scraper.

Scrapes https://myfwc.com/about/overview/careers (Florida Fish & Wildlife)
for state marine biology jobs. Uses HTML parsing with BeautifulSoup4.
"""

import logging
from datetime import datetime

from bs4 import BeautifulSoup

from core.schemas import Job
from scrapers.base_scraper import BaseScraper
from scrapers.scraper_manager import register_scraper

logger = logging.getLogger(__name__)


@register_scraper
class FloridaGovScraper(BaseScraper):
    """Scraper for Florida Fish & Wildlife Conservation Commission job listings."""

    scraper_id = "florida_gov"

    def search(self, query_params: dict | None = None) -> str:
        """
        Fetch the Florida FWC careers page.

        Returns raw HTML.
        """
        url = "https://myfwc.com/about/overview/careers"
        response = self.fetch(url)
        return response.text

    def parse(self, raw_data: str) -> list[Job]:
        """
        Parse Florida FWC HTML to extract job listings.

        Expected structure: job cards with title, location, description.
        Handle missing fields gracefully.
        """
        soup = BeautifulSoup(raw_data, "lxml")
        jobs = []

        # Look for job listings
        job_cards = soup.find_all("div", class_=lambda x: x and "job" in x.lower()) or \
                    soup.find_all("li", class_=lambda x: x and "job" in x.lower()) or \
                    soup.find_all("article") or \
                    soup.find_all("div", class_="position") or \
                    soup.find_all("tr", class_=lambda x: x and "job" in x.lower())

        for idx, card in enumerate(job_cards):
            try:
                # Extract title
                title_elem = card.find("h2") or card.find("h3") or card.find("h4") or \
                             card.find("a", class_=lambda x: x and "title" in x.lower()) or \
                             card.find("a")
                if not title_elem:
                    continue
                title = title_elem.get_text(strip=True)

                # Skip if title suggests external link
                if "peopleFirst" in title or "state personnel" in title.lower():
                    continue

                # Extract URL
                link_elem = card.find("a", href=True)
                if link_elem:
                    url = link_elem["href"]
                    if not url.startswith("http"):
                        url = f"https://myfwc.com{url}"
                else:
                    url = "https://myfwc.com/about/overview/careers"

                # Extract location (default to Florida if not specified)
                location_elem = card.find(class_=lambda x: x and "location" in x.lower()) or \
                               card.find("span", string=lambda s: s and ("location" in s.lower() if s else False))
                location_text = location_elem.get_text(strip=True) if location_elem else None

                city, state = None, "FL"
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
                job_type_text = type_elem.get_text(strip=True).lower() if type_elem else "full-time"
                if "intern" in job_type_text:
                    job_type = "internship"
                elif "volunteer" in job_type_text:
                    job_type = "volunteer"
                elif "part" in job_type_text:
                    job_type = "part-time"
                elif "seasonal" in job_type_text:
                    job_type = "seasonal"
                else:
                    job_type = "full-time"

                job = Job(
                    job_id=f"{self.scraper_id}_{idx}",
                    title=title,
                    employer="Florida Fish & Wildlife Conservation Commission",
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
                logger.warning("Failed to parse Florida FWC job card %d: %s", idx, e)
                continue

        logger.info("Florida Gov scraper found %d jobs", len(jobs))
        return jobs
