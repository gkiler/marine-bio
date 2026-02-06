"""
Conservation Job Board scraper (HTML).

Scrapes marine biology job listings from Conservation Job Board.
"""

import logging

from bs4 import BeautifulSoup

from core.schemas import Job
from scrapers.base_scraper import BaseScraper
from scrapers.scraper_manager import register_scraper

logger = logging.getLogger(__name__)


@register_scraper
class ConservationScraper(BaseScraper):
    """Scraper for Conservation Job Board marine biology category."""

    scraper_id = "conservation"

    def search(self, query_params: dict | None = None) -> list[str]:
        """Fetch all pages of Conservation Job Board marine biology jobs."""
        url = "https://www.conservationjobboard.com/category/marine-biology-jobs"
        # Pagination uses <a rel="next"> in ul.pagination
        return self.fetch_paginated(url, next_link_selector="a[rel='next']", max_pages=10)

    def parse(self, raw_data: list[str]) -> list[Job]:
        """
        Parse job listings from Conservation Job Board (multi-page).

        Verified structure (2026-02):
          div.listing__job
            header.listing__job__header
              h2.listing__job__title > a.gtag-job-link (has href, company attr, job_type attr)
            h3 (employer name, direct child of listing__job)
            i.fa-map-marker-alt + text sibling (location)
            p.listing__job__intro (job type, salary — label in <span>)
            footer > div.listing__job__time (posted ago)
        """
        jobs = []
        pages = raw_data if isinstance(raw_data, list) else [raw_data]

        job_elements = []
        for page_html in pages:
            soup = BeautifulSoup(page_html, "lxml")
            job_elements.extend(soup.find_all("div", class_="listing__job"))
        if not job_elements:
            logger.warning("Conservation Job Board: No div.listing__job elements found")
            return jobs

        for element in job_elements:
            try:
                # Title + URL from h2.listing__job__title > a
                title_h2 = element.find("h2", class_="listing__job__title")
                if not title_h2:
                    continue
                link = title_h2.find("a")
                if not link or not link.get("href"):
                    continue

                title = link.get_text(strip=True)
                url = link["href"]

                # Job code from data attribute for stable ID
                job_code = link.get("data-job-code", "")
                job_id = f"conservation_{job_code}" if job_code else f"conservation_{hash(url) % 1000000}"

                # Employer from h3 (direct child of div.listing__job)
                employer_el = element.find("h3")
                employer = employer_el.get_text(strip=True) if employer_el else (
                    link.get("company", "").replace("-", " ").title() or "Unknown Employer"
                )

                # Location from text after i.fa-map-marker-alt
                location_city = None
                location_state = None
                map_icon = element.find("i", class_="fa-map-marker-alt")
                if map_icon and map_icon.next_sibling:
                    loc_text = (
                        map_icon.next_sibling.strip()
                        if isinstance(map_icon.next_sibling, str)
                        else map_icon.next_sibling.get_text(strip=True)
                    )
                    parts = loc_text.split(",")
                    if len(parts) >= 2:
                        location_city = parts[0].strip()
                        location_state = parts[1].strip()

                # Job type + salary from p.listing__job__intro elements
                job_type = "full-time"
                salary_range = None
                intros = element.find_all("p", class_="listing__job__intro")
                for intro in intros:
                    label = intro.find("span")
                    label_text = label.get_text(strip=True).rstrip(":") if label else ""
                    value = intro.get_text(strip=True).replace(label_text, "").strip().lstrip(":")
                    value = value.strip()

                    if "job type" in label_text.lower():
                        type_map = {
                            "permanent": "full-time",
                            "temporary": "seasonal",
                            "internship": "internship",
                            "volunteer": "volunteer",
                            "part-time": "part-time",
                            "seasonal": "seasonal",
                        }
                        job_type = type_map.get(value.lower(), "full-time")
                    elif "salary" in label_text.lower():
                        salary_range = value if value else None

                # Posted time from div.listing__job__time
                time_el = element.find("div", class_="listing__job__time")
                posted_text = time_el.get_text(strip=True) if time_el else ""

                job = Job(
                    job_id=job_id,
                    title=title,
                    employer=employer,
                    location_city=location_city,
                    location_state=location_state,
                    location_country="USA",
                    remote=False,
                    description=f"{title} at {employer}. {posted_text}.",
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
                logger.error("Error parsing Conservation Job Board job: %s", e)
                continue

        logger.info("Parsed %d jobs from Conservation Job Board", len(jobs))
        return jobs
