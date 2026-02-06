"""
Scripps Institution of Oceanography job scraper.

Scrapes: https://scripps.ucsd.edu/portal/jobs
"""

import logging
from datetime import datetime

from bs4 import BeautifulSoup

from core.schemas import Job
from scrapers.base_scraper import BaseScraper
from scrapers.scraper_manager import register_scraper

logger = logging.getLogger(__name__)


@register_scraper
class ScrippsScraper(BaseScraper):
    """
    Scraper for Scripps Institution of Oceanography jobs.

    Flow:
    1. Fetch jobs portal page
    2. Parse oceanography positions
    3. Extract job details and application links
    """

    scraper_id = "scripps"

    def search(self, query_params: dict | None = None) -> str:
        """Fetch Scripps jobs portal HTML."""
        url = "https://scripps.ucsd.edu/portal/jobs"
        response = self.fetch(url)
        return response.text

    def parse(self, raw_data: str) -> list[Job]:
        """
        Parse Scripps job listings from HTML.

        Verified structure (2026-02):
          section.block-jobs > ul.list > li
            strong > a[href] (title and URL to UCSD employment system)
            text node after <br/> (department info, e.g., "CLIMATE/ATMOS SCI/PHY OCEANOG (100% Career)")

        Note: Jobs link to https://employment.ucsd.edu/jobs?keyword=XXXXXX
        """
        soup = BeautifulSoup(raw_data, "lxml")
        jobs = []

        # Find the jobs block
        jobs_block = soup.find("section", class_="block-jobs")
        if not jobs_block:
            logger.warning("Scripps: No section.block-jobs found")
            return jobs

        # Find the list of jobs
        job_list = jobs_block.find("ul", class_="list")
        if not job_list:
            logger.warning("Scripps: No ul.list found in jobs block")
            return jobs

        list_items = job_list.find_all("li")
        logger.info("Scripps: Found %d job list items", len(list_items))

        for li in list_items:
            try:
                # Get the link (inside <strong>)
                strong = li.find("strong")
                if not strong:
                    continue

                link = strong.find("a", href=True)
                if not link:
                    continue

                url = link["href"]
                # Full title is in link text (e.g., "138123 Field Research and Development Eng. 3")
                full_title = link.get_text(strip=True)

                # Extract job number and title
                parts = full_title.split(" ", 1)
                job_num = parts[0] if parts else hash(url) % 1000000
                title = parts[1] if len(parts) > 1 else full_title

                job_id = f"scripps_{job_num}"

                # Get department/division info (text after <br/>)
                # This is in the text content after the <strong> tag
                dept_text = li.get_text(strip=True).replace(full_title, "").strip()

                # Determine job type from department text
                job_type = "full-time"
                if "career" in dept_text.lower():
                    job_type = "full-time"
                elif "limited" in dept_text.lower() or "temporary" in dept_text.lower():
                    job_type = "seasonal"

                title_lower = title.lower()
                if "intern" in title_lower:
                    job_type = "internship"
                elif "postdoc" in title_lower or "fellow" in title_lower:
                    job_type = "full-time"

                job = Job(
                    job_id=job_id,
                    title=title,
                    employer="Scripps Institution of Oceanography",
                    location_city="La Jolla",
                    location_state="CA",
                    location_country="USA",
                    remote=False,
                    description=f"{title} - {dept_text}" if dept_text else title,
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
                logger.error("Error parsing Scripps job: %s", e)
                continue

        logger.info("Scripps scraper parsed %d jobs", len(jobs))
        return jobs
