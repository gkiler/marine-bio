# NOTE: Pagination requires JavaScript. Scraper fetches first page only.
"""
Blue Jobs marine jobs scraper (HTML).

Scrapes marine job listings from blue-jobs.com.
"""

import logging

from bs4 import BeautifulSoup

from core.schemas import Job
from scrapers.base_scraper import BaseScraper
from scrapers.scraper_manager import register_scraper

logger = logging.getLogger(__name__)


@register_scraper
class BlueJobsScraper(BaseScraper):
    """Scraper for Blue Jobs marine job board."""

    scraper_id = "bluejobs"

    def search(self, query_params: dict | None = None) -> str:
        """Fetch the Blue Jobs homepage listings (first page only)."""
        url = "https://www.blue-jobs.com"
        response = self.fetch(url)
        return response.text

    def parse(self, raw_data: str) -> list[Job]:
        """
        Parse marine job listings from Blue Jobs.

        Verified structure (2026-02):
          article.listing-item
            div.listing-item__title > a (title + URL)
            span.listing-item__info--item-company (employer)
            span.listing-item__info--item-location (location)
            span.listing-item__employment-type (job type)
            div.listing-item__info--item-salary-range (salary)
            div.listing-item__desc (description)
            div.listing-item__date (posted date)
        """
        soup = BeautifulSoup(raw_data, "lxml")
        jobs = []

        job_elements = soup.find_all("article", class_="listing-item")
        if not job_elements:
            logger.warning("Blue Jobs: No article.listing-item elements found")
            return jobs

        for element in job_elements:
            try:
                # Title + URL from div.listing-item__title > a
                title_div = element.find("div", class_="listing-item__title")
                if not title_div:
                    continue
                link = title_div.find("a")
                if not link or not link.get("href"):
                    continue

                title = link.get_text(strip=True)
                url = link["href"]
                if not url.startswith("http"):
                    url = f"https://www.blue-jobs.com{url}"

                # Job ID from URL
                job_id = f"bluejobs_{hash(url) % 1000000}"

                # Employer from span.listing-item__info--item-company
                employer_elem = element.find("span", class_="listing-item__info--item-company")
                employer = employer_elem.get_text(strip=True) if employer_elem else "Unknown Employer"

                # Location from span.listing-item__info--item-location
                location_city = None
                location_state = None
                location_country = "Unknown"
                remote = False
                location_elem = element.find("span", class_="listing-item__info--item-location")
                if location_elem:
                    location_text = location_elem.get_text(strip=True)
                    # Check for remote
                    if "remote" in location_text.lower():
                        remote = True
                    # Parse location (could be "City, Country" or "Hybrid (City, Country)")
                    if "(" in location_text:
                        location_text = location_text.split("(")[-1].rstrip(")")
                    parts = [p.strip() for p in location_text.split(",")]
                    if len(parts) >= 1:
                        location_city = parts[0]
                    if len(parts) >= 2:
                        location_country = parts[-1]
                        if len(parts) == 3:
                            location_state = parts[1]

                # Job type from span.listing-item__employment-type
                job_type = "full-time"
                type_elem = element.find("span", class_="listing-item__employment-type")
                if type_elem:
                    type_text = type_elem.get_text(strip=True).lower()
                    if "intern" in type_text:
                        job_type = "internship"
                    elif "part" in type_text:
                        job_type = "part-time"
                    elif "seasonal" in type_text or "field work" in type_text:
                        job_type = "seasonal"
                    elif "volunteer" in type_text:
                        job_type = "volunteer"

                # Salary from div.listing-item__info--item-salary-range
                salary_range = None
                salary_elem = element.find("div", class_="listing-item__info--item-salary-range")
                if salary_elem:
                    salary_text = salary_elem.get_text(strip=True)
                    if salary_text:
                        salary_range = salary_text

                # Description from div.listing-item__desc
                desc_elem = element.find("div", class_="listing-item__desc")
                description = desc_elem.get_text(strip=True) if desc_elem else f"{title} at {employer}"

                # Posted date from div.listing-item__date
                posted_text = ""
                date_elem = element.find("div", class_="listing-item__date")
                if date_elem:
                    posted_text = date_elem.get_text(strip=True)

                job = Job(
                    job_id=job_id,
                    title=title,
                    employer=employer,
                    location_city=location_city,
                    location_state=location_state,
                    location_country=location_country,
                    remote=remote,
                    description=f"{description}. Posted: {posted_text}." if posted_text else description,
                    requirements=[],
                    salary_range=salary_range,
                    job_type=job_type,
                    posted_date=None,
                    application_deadline=None,
                    url=url,
                    source=self.scraper_id,
                )
                jobs.append(job)

            except Exception as e:
                logger.error("Error parsing Blue Jobs listing: %s", e)
                continue

        logger.info("Parsed %d jobs from Blue Jobs", len(jobs))
        return jobs
