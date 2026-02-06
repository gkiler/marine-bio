"""
USAJOBS federal job board scraper (API-based).

Uses the official USAJOBS REST API with authentication.
Searches for marine biology, oceanography, and fisheries positions.
"""

import logging
from datetime import datetime

from config.settings import settings
from core.schemas import Job
from scrapers.base_scraper import BaseScraper
from scrapers.scraper_manager import register_scraper

logger = logging.getLogger(__name__)


@register_scraper
class USAJobsScraper(BaseScraper):
    """Scraper for federal jobs via USAJOBS API."""

    scraper_id = "usajobs"
    rate_per_minute = 15  # API rate limit

    def search(self, query_params: dict | None = None) -> dict:
        """
        Fetch jobs from USAJOBS API.

        Default search: marine biology OR oceanography OR fisheries.
        API docs: https://developer.usajobs.gov/Search-API/Calling-the-API
        """
        url = "https://data.usajobs.gov/api/search"

        # Build search parameters
        params = query_params or {}
        if "Keyword" not in params:
            params["Keyword"] = "marine biology OR oceanography OR fisheries"

        # Required headers for USAJOBS API
        headers = {
            "Authorization-Key": settings.usajobs_api_key,
            "Host": "data.usajobs.gov",
            "User-Agent": f"marine-bio-jobs@example.com ({settings.usajobs_email})",
        }

        # Override client headers for this request
        original_headers = self.client.headers.copy()
        self.client.headers.update(headers)

        try:
            response = self.fetch(url, params=params)
            return response.json()
        finally:
            # Restore original headers
            self.client.headers = original_headers

    def parse(self, raw_data: dict) -> list[Job]:
        """
        Parse USAJOBS API JSON response.

        Response structure:
        {
          "SearchResult": {
            "SearchResultItems": [
              {
                "MatchedObjectDescriptor": {
                  "PositionID": "...",
                  "PositionTitle": "...",
                  "OrganizationName": "...",
                  "PositionLocationDisplay": "...",
                  "PositionLocation": [{"CityName": "...", "State": "..."}],
                  "RemoteIndicator": bool,
                  "UserArea": {
                    "Details": {
                      "JobSummary": "...",
                      "MajorDuties": ["..."],
                      "LowGrade": "...",
                      "HighGrade": "...",
                      "SalaryMin": ...,
                      "SalaryMax": ...
                    }
                  },
                  "PublicationStartDate": "...",
                  "ApplicationCloseDate": "...",
                  "ApplyURI": ["..."]
                }
              }
            ]
          }
        }
        """
        jobs = []

        search_result = raw_data.get("SearchResult", {})
        items = search_result.get("SearchResultItems", [])

        if not items:
            logger.info("USAJOBS returned no results")
            return jobs

        for item in items:
            try:
                descriptor = item.get("MatchedObjectDescriptor", {})

                # Required fields
                position_id = descriptor.get("PositionID")
                title = descriptor.get("PositionTitle")
                employer = descriptor.get("OrganizationName")
                apply_urls = descriptor.get("ApplyURI", [])

                if not all([position_id, title, employer, apply_urls]):
                    logger.warning("Skipping USAJOBS item with missing required fields")
                    continue

                # Location
                locations = descriptor.get("PositionLocation", [])
                location_city = None
                location_state = None
                if locations:
                    location_city = locations[0].get("CityName")
                    location_state = locations[0].get("State")

                remote = descriptor.get("RemoteIndicator", False)

                # Description and requirements
                user_area = descriptor.get("UserArea", {})
                details = user_area.get("Details", {})
                summary = details.get("JobSummary", "")
                duties = details.get("MajorDuties", [])

                # Combine summary and duties
                description_parts = [summary]
                if duties:
                    description_parts.append("\n\nMajor Duties:\n" + "\n".join(f"- {d}" for d in duties))
                description = "\n".join(description_parts).strip() or "No description available"

                # Qualifications as requirements
                qualifications = details.get("Qualifications", "")
                requirements = [qualifications] if qualifications else []

                # Salary
                salary_min = details.get("SalaryMin")
                salary_max = details.get("SalaryMax")
                salary_range = None
                if salary_min and salary_max:
                    salary_range = f"${salary_min:,} - ${salary_max:,}"
                elif salary_min:
                    salary_range = f"From ${salary_min:,}"

                # Job type (federal jobs are typically full-time)
                job_type = "full-time"

                # Dates
                posted_date = None
                if pub_date := descriptor.get("PublicationStartDate"):
                    try:
                        posted_date = datetime.fromisoformat(pub_date.replace("Z", "+00:00"))
                    except ValueError:
                        logger.warning("Invalid posted_date: %s", pub_date)

                application_deadline = None
                if close_date := descriptor.get("ApplicationCloseDate"):
                    try:
                        application_deadline = datetime.fromisoformat(close_date.replace("Z", "+00:00"))
                    except ValueError:
                        logger.warning("Invalid application_deadline: %s", close_date)

                # URL
                url = apply_urls[0]

                job = Job(
                    job_id=f"usajobs_{position_id}",
                    title=title,
                    employer=employer,
                    location_city=location_city,
                    location_state=location_state,
                    location_country="USA",
                    remote=remote,
                    description=description,
                    requirements=requirements,
                    salary_range=salary_range,
                    job_type=job_type,
                    posted_date=posted_date,
                    application_deadline=application_deadline,
                    url=url,
                    source=self.scraper_id,
                )
                jobs.append(job)

            except Exception as e:
                logger.error("Error parsing USAJOBS item: %s", e)
                continue

        logger.info("Parsed %d jobs from USAJOBS", len(jobs))
        return jobs
