"""
Abstract base scraper with caching, rate limiting, and retries.

All scrapers inherit from BaseScraper and implement:
  - search(query_params) → fetch raw HTML/JSON from the source
  - parse(raw_data) → extract Job objects from the response

The base class handles: caching, rate limiting, retries, error wrapping.
"""

import logging
import time
from abc import ABC, abstractmethod

import httpx
from bs4 import BeautifulSoup
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from config.settings import settings
from core.exceptions import RateLimitError, ScraperError
from core.schemas import Job, ScraperResult
from utils.cache import FileCache
from utils.rate_limiter import TokenBucket, rate_limiters

logger = logging.getLogger(__name__)


class BaseScraper(ABC):
    """
    Abstract base for all job scrapers.

    Subclasses must define:
      - scraper_id: str (matches config/sources.py scraper_id)
      - search(query_params) → raw response data
      - parse(raw_data) → list[Job]

    The base class provides:
      - run() orchestrator with cache check → fetch → parse → cache store
      - HTTP client with rate limiting and retries
      - Error wrapping with scraper context
    """

    scraper_id: str = ""
    rate_per_minute: int | None = None  # Override per-scraper if needed

    def __init__(self) -> None:
        self.cache = FileCache()
        self.limiter: TokenBucket = rate_limiters.get(
            self.scraper_id, self.rate_per_minute
        )
        self.client = httpx.Client(
            timeout=settings.request_timeout_seconds,
            follow_redirects=True,
            headers={
                "User-Agent": (
                    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/131.0.0.0 Safari/537.36"
                ),
                "Accept": (
                    "text/html,application/xhtml+xml,application/xml;q=0.9,"
                    "image/avif,image/webp,image/apng,*/*;q=0.8"
                ),
                "Accept-Language": "en-US,en;q=0.9",
                "Sec-Ch-Ua": '"Google Chrome";v="131", "Chromium";v="131", "Not_A Brand";v="24"',
                "Sec-Ch-Ua-Mobile": "?0",
                "Sec-Ch-Ua-Platform": '"macOS"',
                "Sec-Fetch-Dest": "document",
                "Sec-Fetch-Mode": "navigate",
                "Sec-Fetch-Site": "none",
                "Sec-Fetch-User": "?1",
                "Upgrade-Insecure-Requests": "1",
            },
        )

    def run(self, query_params: dict | None = None) -> ScraperResult:
        """
        Full scrape pipeline: cache check → fetch → parse → cache store.

        Returns ScraperResult with jobs and metadata. Never raises —
        errors are captured in result.errors.
        """
        start = time.time()

        # Check cache first
        cached = self.cache.get(self.scraper_id, query_params)
        if cached is not None:
            jobs = [Job(**j) for j in cached]
            return ScraperResult(
                source=self.scraper_id,
                jobs=jobs,
                total_found=len(jobs),
                duration_seconds=time.time() - start,
            )

        # Fetch and parse
        try:
            raw_data = self.search(query_params)
            jobs = self.parse(raw_data)

            # Cache the results
            self.cache.store(
                self.scraper_id,
                [j.model_dump(mode="json") for j in jobs],
                query_params,
            )

            return ScraperResult(
                source=self.scraper_id,
                jobs=jobs,
                total_found=len(jobs),
                duration_seconds=time.time() - start,
            )

        except RateLimitError:
            raise  # Let caller handle rate limits
        except Exception as e:
            logger.error("Scraper %s failed: %s", self.scraper_id, e)
            return ScraperResult(
                source=self.scraper_id,
                errors=[str(e)],
                duration_seconds=time.time() - start,
            )

    @retry(
        stop=stop_after_attempt(settings.max_retries),
        wait=wait_exponential(
            multiplier=settings.retry_backoff_seconds, min=1, max=30
        ),
        retry=retry_if_exception_type((httpx.HTTPStatusError, httpx.ConnectError)),
        reraise=True,
    )
    def fetch(self, url: str, params: dict | None = None) -> httpx.Response:
        """
        HTTP GET with rate limiting and retries.

        Raises ScraperError on non-retryable failures.
        Raises RateLimitError on 429.
        """
        self.limiter.acquire_sync()

        response = self.client.get(url, params=params)

        if response.status_code == 429:
            retry_after = response.headers.get("Retry-After")
            raise RateLimitError(
                self.scraper_id,
                url,
                int(retry_after) if retry_after else None,
            )

        if response.status_code >= 400:
            raise ScraperError(
                self.scraper_id,
                f"HTTP {response.status_code}: {response.reason_phrase}",
                url,
            )

        return response

    def fetch_paginated(
        self,
        first_url: str,
        next_link_selector: str = "a[rel='next']",
        max_pages: int = 10,
    ) -> list[str]:
        """
        Fetch multiple pages by following "next" links.

        Args:
            first_url: URL of the first page.
            next_link_selector: CSS selector for the "next page" link.
            max_pages: Safety cap to avoid infinite loops.

        Returns list of HTML strings, one per page.
        """
        pages: list[str] = []
        url: str | None = first_url

        for page_num in range(max_pages):
            if url is None:
                break

            response = self.fetch(url)
            html = response.text
            pages.append(html)
            logger.debug("%s: fetched page %d (%s)", self.scraper_id, page_num + 1, url)

            # Find next page link
            soup = BeautifulSoup(html, "lxml")
            next_link = soup.select_one(next_link_selector)
            if next_link and next_link.get("href"):
                next_url = next_link["href"]
                # Handle relative URLs
                if next_url.startswith("/"):
                    from urllib.parse import urlparse
                    parsed = urlparse(url)
                    next_url = f"{parsed.scheme}://{parsed.netloc}{next_url}"
                url = next_url
            else:
                url = None

        logger.info("%s: fetched %d pages", self.scraper_id, len(pages))
        return pages

    @abstractmethod
    def search(self, query_params: dict | None = None) -> str | dict | list[str]:
        """
        Fetch raw data from the job source.

        Returns HTML string, parsed JSON dict, or list of HTML strings
        (when using pagination via fetch_paginated).
        """
        ...

    @abstractmethod
    def parse(self, raw_data: str | dict | list[str]) -> list[Job]:
        """
        Parse raw response into Job objects.

        raw_data may be a single HTML string, a JSON dict, or a list of
        HTML page strings (pagination). Should handle missing fields
        gracefully — set to None rather than crash.
        """
        ...

    def close(self) -> None:
        """Clean up HTTP client."""
        self.client.close()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()
