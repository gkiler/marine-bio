"""
Florida government marine careers scraper.

Florida FWC careers page at https://myfwc.com/get-involved/employment/careers/
redirects to the state job portal at jobs.myflorida.com for actual job listings.

This scraper uses the state job portal's FWC-filtered search.

Flow:
1. Fetch jobs.myflorida.com with FWC filter
2. Parse job listings (if HTML-based) or handle redirect
3. Extract job details and create Job objects
"""

import logging

from core.exceptions import ScraperError
from core.schemas import Job
from scrapers.base_scraper import BaseScraper
from scrapers.scraper_manager import register_scraper

logger = logging.getLogger(__name__)


@register_scraper
class FloridaGovScraper(BaseScraper):
    """
    Scraper for Florida Fish & Wildlife Conservation Commission job listings.

    FWC jobs are hosted on the state job portal at jobs.myflorida.com.
    The site appears to use a complex JavaScript-based ATS system.
    """

    scraper_id = "florida_gov"

    def search(self, query_params: dict | None = None) -> str:
        """
        Fetch the Florida state jobs portal filtered for FWC positions.

        URL: https://jobs.myflorida.com/search/?searchby=location&createNewAlert=false&q=FWC
        """
        url = "https://jobs.myflorida.com/search/"
        params = {
            "searchby": "location",
            "createNewAlert": "false",
            "q": "FWC",
        }

        if query_params:
            params.update(query_params)

        logger.info("Fetching Florida FWC jobs from state portal")
        response = self.fetch(url, params=params)
        return response.text

    def parse(self, raw_data: str) -> list[Job]:
        """
        Parse Florida state jobs portal HTML to extract FWC job listings.

        The portal uses table rows with class="data-row" for job listings.
        Each row contains title, location, and posted date in specific columns.
        """
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(raw_data, "lxml")
        jobs = []

        # Jobs are in table rows with data-row class
        job_rows = soup.find_all("tr", class_="data-row")

        if not job_rows:
            logger.warning("No job rows found - portal structure may have changed")
            return jobs

        for idx, row in enumerate(job_rows):
            try:
                # Extract title and URL from td.colTitle > span.jobTitle > a
                title_cell = row.find("td", class_="colTitle")
                if not title_cell:
                    continue

                title_link = title_cell.find("a", class_="jobTitle-link")
                if not title_link:
                    continue

                title = title_link.get_text(strip=True)
                url = title_link.get("href", "")
                if url and not url.startswith("http"):
                    url = f"https://jobs.myflorida.com{url}"

                # Extract location from td.colLocation
                location_cell = row.find("td", class_="colLocation")
                location_text = location_cell.get_text(strip=True) if location_cell else None

                city = None
                state = "FL"
                remote = False

                if location_text:
                    remote = "remote" in location_text.lower()
                    # Location format is typically "CITY-STATE-ZIP" or "CITY, FL"
                    location_text = location_text.replace("-FL-", ", FL,")
                    parts = [p.strip() for p in location_text.split(",")]
                    if parts:
                        city = parts[0]
                    if len(parts) > 1:
                        state = parts[1]

                # Extract posted date from td.colDate
                date_cell = row.find("td", class_="colDate")
                posted_date = None
                if date_cell:
                    date_text = date_cell.get_text(strip=True)
                    # Try to parse date
                    from datetime import datetime
                    for fmt in ["%m/%d/%Y", "%Y-%m-%d", "%b %d, %Y"]:
                        try:
                            posted_date = datetime.strptime(date_text, fmt)
                            break
                        except ValueError:
                            continue

                # Description is not in the table, use title for now
                description = f"Florida FWC position: {title}"

                # Determine job type from title
                job_type = "full-time"
                title_lower = title.lower()
                if "intern" in title_lower:
                    job_type = "internship"
                elif "volunteer" in title_lower:
                    job_type = "volunteer"
                elif "part-time" in title_lower or "part time" in title_lower:
                    job_type = "part-time"
                elif "seasonal" in title_lower or "temporary" in title_lower or "temp" in title_lower:
                    job_type = "seasonal"

                # Generate unique job ID from URL or index
                if url:
                    url_parts = url.split("/")
                    source_id = url_parts[-2] if len(url_parts) > 1 else str(idx)
                else:
                    source_id = str(idx)

                job = Job(
                    job_id=f"{self.scraper_id}_{source_id}",
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
                    posted_date=posted_date,
                    application_deadline=None,
                    url=url,
                    source=self.scraper_id,
                )
                jobs.append(job)

            except Exception as e:
                logger.warning("Failed to parse Florida FWC job row %d: %s", idx, e)
                continue

        logger.info("Florida Gov scraper found %d jobs", len(jobs))
        return jobs
