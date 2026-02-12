"""
World Wildlife Fund careers scraper.

Scrapes WWF's iCIMS job board at https://careers-wwfus.icims.com/jobs/search
for conservation jobs. Uses HTML parsing with BeautifulSoup4.
"""

import logging
import re
from datetime import datetime

from bs4 import BeautifulSoup

from core.schemas import Job
from scrapers.base_scraper import BaseScraper
from scrapers.scraper_manager import register_scraper

logger = logging.getLogger(__name__)


@register_scraper
class WwfScraper(BaseScraper):
    """Scraper for World Wildlife Fund job listings via iCIMS."""

    scraper_id = "wwf"

    def search(self, query_params: dict | None = None) -> str:
        """
        Fetch the WWF iCIMS job board (iframe version for direct HTML access).

        Returns raw HTML.
        """
        url = "https://careers-wwfus.icims.com/jobs/search?in_iframe=1"
        response = self.fetch(url)
        return response.text

    def parse(self, raw_data: str) -> list[Job]:
        """
        Parse iCIMS HTML to extract WWF job listings.

        Expected structure: div.row containing:
        - div.col-xs-6.header.left > location span
        - div.col-xs-6.header.right > posted date span
        - div.col-xs-12.title > a.iCIMS_Anchor > h3 (title + link)
        - div.col-xs-12.description > job description text
        """
        soup = BeautifulSoup(raw_data, "lxml")
        jobs = []

        # Find all job rows (skip the first row which is the table header)
        job_rows = soup.find_all("div", class_="row")

        for idx, row in enumerate(job_rows):
            try:
                # Extract title and URL
                title_div = row.find("div", class_="title")
                if not title_div:
                    continue

                h3 = title_div.find("h3")
                link = title_div.find("a", class_="iCIMS_Anchor")
                if not h3 or not link:
                    continue

                title = h3.get_text(strip=True)
                url = link["href"]
                if not url.startswith("http"):
                    url = f"https://careers-wwfus.icims.com{url}"

                # Extract location from left header
                # Class attribute is a list, need to check for both 'header' and 'left'
                location_div = row.find("div", class_=lambda x: x and "header" in x and "left" in x)
                location_text = None
                city, state = None, None
                remote = False

                if location_div:
                    # Get all spans, exclude sr-only ones
                    spans = location_div.find_all("span")
                    for span in spans:
                        classes = span.get("class", [])
                        if "sr-only" not in classes and "field-label" not in classes:
                            location_text = span.get_text(strip=True)
                            break

                    if location_text:
                        remote = "remote" in location_text.lower()

                        # Parse location format: US-ST-City
                        parts = location_text.split("-")
                        if len(parts) >= 3:
                            state = parts[1]
                            city = parts[2]
                        elif len(parts) == 2:
                            state = parts[1]

                # Extract posted date from right header
                posted_date = None
                date_div = row.find("div", class_=lambda x: x and "header" in x and "right" in x)
                if date_div:
                    date_span = date_div.find("span", title=True)
                    if date_span and date_span.get("title"):
                        date_str = date_span["title"]
                        try:
                            # Parse format: "2/11/2026 2:00 PM"
                            posted_date = datetime.strptime(date_str, "%m/%d/%Y %I:%M %p")
                        except ValueError:
                            logger.debug("Could not parse date: %s", date_str)

                # Extract description
                desc_div = row.find("div", class_="description")
                description = desc_div.get_text(strip=True) if desc_div else title

                # Determine job type from title
                title_lower = title.lower()
                if "intern" in title_lower:
                    job_type = "internship"
                elif "volunteer" in title_lower:
                    job_type = "volunteer"
                elif "part" in title_lower or "part-time" in title_lower:
                    job_type = "part-time"
                else:
                    job_type = "full-time"

                job = Job(
                    job_id=f"{self.scraper_id}_{idx}",
                    title=title,
                    employer="World Wildlife Fund",
                    location_city=city,
                    location_state=state,
                    location_country="USA",
                    remote=remote,
                    description=description,
                    requirements=[],
                    salary_range=None,
                    job_type=job_type,
                    posted_date=posted_date,
                    application_deadline=None,
                    url=url,
                    source=self.scraper_id,
                )
                jobs.append(job)

            except Exception as e:
                logger.warning("Failed to parse WWF job row %d: %s", idx, e)
                continue

        logger.info("WWF scraper found %d jobs", len(jobs))
        return jobs
