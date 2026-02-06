"""
Token bucket rate limiter for scrapers.

Each scraper gets its own bucket. Requests consume tokens;
tokens refill at a steady rate. If bucket is empty, caller
must wait before making the next request.
"""

import asyncio
import time

from config.settings import settings


class TokenBucket:
    """
    Token bucket rate limiter.

    Flow: acquire() → wait if needed → return when token available.
    Tokens refill at `rate` per second, up to `burst` max.
    """

    def __init__(
        self,
        rate_per_minute: int | None = None,
        burst: int | None = None,
    ):
        rpm = rate_per_minute or settings.default_requests_per_minute
        self.rate = rpm / 60.0  # tokens per second
        self.burst = burst or settings.default_burst_size
        self.tokens = float(self.burst)
        self.last_refill = time.monotonic()

    def _refill(self) -> None:
        """Add tokens based on elapsed time since last refill."""
        now = time.monotonic()
        elapsed = now - self.last_refill
        self.tokens = min(self.burst, self.tokens + elapsed * self.rate)
        self.last_refill = now

    def acquire_sync(self) -> float:
        """
        Block until a token is available (synchronous).

        Returns the number of seconds waited.
        """
        self._refill()
        if self.tokens >= 1.0:
            self.tokens -= 1.0
            return 0.0

        # Calculate wait time for next token
        deficit = 1.0 - self.tokens
        wait_time = deficit / self.rate
        time.sleep(wait_time)
        self._refill()
        self.tokens -= 1.0
        return wait_time

    async def acquire(self) -> float:
        """
        Wait until a token is available (async).

        Returns the number of seconds waited.
        """
        self._refill()
        if self.tokens >= 1.0:
            self.tokens -= 1.0
            return 0.0

        deficit = 1.0 - self.tokens
        wait_time = deficit / self.rate
        await asyncio.sleep(wait_time)
        self._refill()
        self.tokens -= 1.0
        return wait_time


class RateLimiterRegistry:
    """
    Registry of per-scraper rate limiters.

    Usage:
        limiter = registry.get("usajobs")
        await limiter.acquire()
    """

    def __init__(self) -> None:
        self._buckets: dict[str, TokenBucket] = {}

    def get(
        self,
        scraper_id: str,
        rate_per_minute: int | None = None,
        burst: int | None = None,
    ) -> TokenBucket:
        """Get or create a rate limiter for a scraper."""
        if scraper_id not in self._buckets:
            self._buckets[scraper_id] = TokenBucket(rate_per_minute, burst)
        return self._buckets[scraper_id]


# Global registry — import and use across all scrapers
rate_limiters = RateLimiterRegistry()
