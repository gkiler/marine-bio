"""
Data models for the marine bio job aggregator.

Job: a single job listing from any source.
ScraperResult: the output of running a scraper (jobs + metadata).
"""

from datetime import datetime

from pydantic import BaseModel, Field, computed_field


class Job(BaseModel):
    """A single job listing scraped from any source."""

    job_id: str = Field(description="Unique ID: {source}_{source_unique_id}")
    title: str
    employer: str
    location_city: str | None = None
    location_state: str | None = None
    location_country: str = "USA"
    remote: bool = False
    description: str
    requirements: list[str] = Field(default_factory=list)
    salary_range: str | None = None
    job_type: str = Field(
        description="full-time, part-time, internship, volunteer, seasonal"
    )
    posted_date: datetime | None = None
    application_deadline: datetime | None = None
    url: str = Field(description="Direct link to the job posting / application")
    source: str = Field(description="Scraper ID that found this job")
    is_entry_level: bool | None = Field(
        default=None,
        description="None = unclassified. Set by keyword filter or Gemini classifier.",
    )
    scraped_at: datetime = Field(default_factory=datetime.now)

    @computed_field
    @property
    def location_display(self) -> str:
        """Human-readable location string."""
        parts = [p for p in [self.location_city, self.location_state] if p]
        location = ", ".join(parts) if parts else self.location_country
        if self.remote:
            location = f"{location} (Remote)" if parts else "Remote"
        return location


class ScraperResult(BaseModel):
    """Output from running a single scraper."""

    source: str = Field(description="Scraper ID")
    jobs: list[Job] = Field(default_factory=list)
    total_found: int = 0
    errors: list[str] = Field(default_factory=list)
    scraped_at: datetime = Field(default_factory=datetime.now)
    duration_seconds: float = 0.0

    @computed_field
    @property
    def success(self) -> bool:
        return len(self.errors) == 0
