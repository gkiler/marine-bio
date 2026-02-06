"""
Custom exceptions for the marine bio job aggregator.

All exceptions include context about what went wrong and where.
"""


class ScraperError(Exception):
    """Raised when a scraper fails to fetch or parse job listings."""

    def __init__(self, scraper_id: str, message: str, url: str = ""):
        self.scraper_id = scraper_id
        self.url = url
        detail = f"[{scraper_id}] {message}"
        if url:
            detail += f" (url={url})"
        super().__init__(detail)


class RateLimitError(ScraperError):
    """Raised when a source returns HTTP 429 or equivalent."""

    def __init__(self, scraper_id: str, url: str = "", retry_after: int | None = None):
        self.retry_after = retry_after
        msg = "Rate limited"
        if retry_after:
            msg += f", retry after {retry_after}s"
        super().__init__(scraper_id, msg, url)


class CacheError(Exception):
    """Raised when cache read/write fails. Non-fatal — scraper should continue."""

    def __init__(self, message: str, path: str = ""):
        detail = message
        if path:
            detail += f" (path={path})"
        super().__init__(detail)
