"""
Parser tests against small hand-written fixtures shaped like each source's
response. The fixtures are synthetic; no live pages are stored or fetched.
"""

from scrapers.conservation_scraper import ConservationScraper
from scrapers.usajobs_scraper import USAJobsScraper

USAJOBS_RESPONSE = {
    "SearchResult": {
        "SearchResultItems": [
            {
                "MatchedObjectDescriptor": {
                    "PositionID": "NOAA-26-001",
                    "PositionTitle": "Biological Science Technician",
                    "OrganizationName": "National Oceanic and Atmospheric Administration",
                    "PositionLocation": [{"CityName": "Honolulu", "State": "Hawaii"}],
                    "RemoteIndicator": False,
                    "UserArea": {
                        "Details": {
                            "JobSummary": "Supports reef monitoring surveys.",
                            "MajorDuties": ["Collects field samples", "Enters survey data"],
                            "Qualifications": "Bachelor's degree in biology.",
                            "SalaryMin": 52000,
                            "SalaryMax": 67000,
                        }
                    },
                    "PublicationStartDate": "2026-02-01T00:00:00Z",
                    "ApplicationCloseDate": "2026-03-01T23:59:59Z",
                    "ApplyURI": ["https://www.usajobs.gov/job/000000000"],
                }
            },
            {
                # Missing title and apply URL: skipped
                "MatchedObjectDescriptor": {"PositionID": "NOAA-26-002"}
            },
        ]
    }
}

CONSERVATION_PAGE = """
<html><body>
<div class="listing__job">
  <header class="listing__job__header">
    <h2 class="listing__job__title">
      <a class="gtag-job-link" href="https://example.org/jobs/sea-turtle-intern" data-job-code="4821">
        Sea Turtle Research Intern
      </a>
    </h2>
  </header>
  <h3>Coastal Turtle Project</h3>
  <i class="fas fa-map-marker-alt"></i> Jupiter, FL
  <p class="listing__job__intro"><span>Job Type:</span> Temporary</p>
  <p class="listing__job__intro"><span>Salary:</span> $500/week</p>
  <footer><div class="listing__job__time">3 days ago</div></footer>
</div>
<div class="listing__job">
  <header class="listing__job__header">
    <h2 class="listing__job__title">No link here</h2>
  </header>
</div>
</body></html>
"""


def test_usajobs_parse():
    with USAJobsScraper() as scraper:
        jobs = scraper.parse(USAJOBS_RESPONSE)

    assert len(jobs) == 1
    job = jobs[0]
    assert job.job_id == "usajobs_NOAA-26-001"
    assert job.title == "Biological Science Technician"
    assert job.location_display == "Honolulu, Hawaii"
    assert job.salary_range == "$52,000 - $67,000"
    assert "Major Duties:" in job.description
    assert "- Enters survey data" in job.description
    assert job.requirements == ["Bachelor's degree in biology."]
    assert job.posted_date.year == 2026 and job.posted_date.month == 2
    assert job.url == "https://www.usajobs.gov/job/000000000"


def test_usajobs_parse_empty_response():
    with USAJobsScraper() as scraper:
        assert scraper.parse({}) == []


def test_conservation_parse():
    with ConservationScraper() as scraper:
        jobs = scraper.parse([CONSERVATION_PAGE])

    assert len(jobs) == 1
    job = jobs[0]
    assert job.job_id == "conservation_4821"
    assert job.title == "Sea Turtle Research Intern"
    assert job.employer == "Coastal Turtle Project"
    assert (job.location_city, job.location_state) == ("Jupiter", "FL")
    assert job.job_type == "seasonal"
    assert job.salary_range == "$500/week"
    assert job.url == "https://example.org/jobs/sea-turtle-intern"
    assert "3 days ago" in job.description


def test_conservation_parse_page_without_listings():
    with ConservationScraper() as scraper:
        assert scraper.parse(["<html><body></body></html>"]) == []
